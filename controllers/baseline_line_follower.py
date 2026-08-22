#!/usr/bin/env python3
"""Hagyományos (AI nélküli) vonalkövető baseline kontroller - M09.

Állapotgép (VONALON / KERESÉS) + P-szabályozó a bal/jobb szenzor
intenzitáskülönbségére. Kizárólag az observe válasz sensor_left/
center/right mezőire támaszkodik, nem használja a position/speed
privilegizált szimulátor-mezőket.

Lásd docs/m09-plan.md a tervezési döntésekért.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4


ALAPERTELMEZETT_HOST = "127.0.0.1"
ALAPERTELMEZETT_PORT = 8765
MAXIMALIS_FRAME_MERET = 16 * 1024
NAPLO_FAJL = Path(__file__).resolve().parent.parent / "logs" / "m09_runs.jsonl"

# --- Szabályozó paraméterek (docs/m09-plan.md) ---
MOVE_LEPES_M = 0.08
MOVE_SEBESSEG = 0.20
TURN_MIN_FOK = 1.0
TURN_MAX_FOK = 5.0
TURN_SEBESSEG = 20.0
P_EROSITES = 8.0
HOLTSAV = 0.02

KERESES_FORDULAT_FOK = 3.0
KERESES_MAX_LEPES = 40


class Allapot(Enum):
    VONALON = "VONALON"
    KERESES = "KERESES"


@dataclass
class FutasStatisztika:
    lepesek_szama: int = 0
    parancsok_szama: int = 0
    vonalvesztesek_szama: int = 0
    palyaelhagyas: bool = False
    kezdet: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class GatewayKliens:
    def __init__(self, host: str, port: int) -> None:
        self.socket = socket.create_connection((host, port), timeout=5)
        self.socket.settimeout(None)

    def kuld(self, parancs: dict[str, Any]) -> dict[str, Any]:
        parancs = {"request_id": str(uuid4()), **parancs}
        payload = json.dumps(
            parancs, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        if not 1 <= len(payload) <= MAXIMALIS_FRAME_MERET:
            raise ValueError("A kimeno JSON tul nagy vagy ures.")

        self.socket.sendall(len(payload).to_bytes(4, "big", signed=False))
        self.socket.sendall(payload)

        hossz_prefix = self._pontosan_fogad(4)
        valasz_hossz = int.from_bytes(hossz_prefix, "big", signed=False)
        valasz_payload = self._pontosan_fogad(valasz_hossz)
        return json.loads(valasz_payload.decode("utf-8"))

    def _pontosan_fogad(self, hossz: int) -> bytes:
        reszek: list[bytes] = []
        hatralevo = hossz
        while hatralevo:
            adat = self.socket.recv(hatralevo)
            if not adat:
                raise ConnectionError("A kapcsolat varatlanul megszakadt.")
            reszek.append(adat)
            hatralevo -= len(adat)
        return b"".join(reszek)

    def close(self) -> None:
        self.socket.close()


def hibajel_szamitasa(observe_valasz: dict[str, Any]) -> float:
    """Pozitiv -> a vonal jobbra van, negativ -> balra van."""
    bal = observe_valasz["sensor_left"]["intensity"]
    jobb = observe_valasz["sensor_right"]["intensity"]
    return jobb - bal


def mindharom_nem_feher(observe_valasz: dict[str, Any]) -> bool:
    return not (
        observe_valasz["sensor_left"]["white"]
        or observe_valasz["sensor_center"]["white"]
        or observe_valasz["sensor_right"]["white"]
    )


def egy_lepes_vonalon(
    kliens: GatewayKliens,
    stat: FutasStatisztika,
    utolso_elojel: list[int],
) -> Allapot:
    observe = kliens.kuld({"command": "observe"})
    stat.parancsok_szama += 1

    if mindharom_nem_feher(observe):
        stat.vonalvesztesek_szama += 1
        return Allapot.KERESES

    hiba = hibajel_szamitasa(observe)
    if abs(hiba) > HOLTSAV:
        utolso_elojel[0] = 1 if hiba > 0 else -1
        korrekcio_fok = max(TURN_MIN_FOK, min(TURN_MAX_FOK, abs(hiba) * P_EROSITES))
        szog = korrekcio_fok if hiba > 0 else -korrekcio_fok
        kliens.kuld(
            {"command": "turn", "angle_deg": szog, "max_angular_speed": TURN_SEBESSEG}
        )
        stat.parancsok_szama += 1

    kliens.kuld(
        {"command": "move", "distance_m": MOVE_LEPES_M, "max_speed": MOVE_SEBESSEG}
    )
    stat.parancsok_szama += 1
    return Allapot.VONALON


def egy_lepes_kereses(
    kliens: GatewayKliens,
    stat: FutasStatisztika,
    utolso_elojel: list[int],
    kereses_lepesek: list[int],
) -> Allapot:
    irany = utolso_elojel[0] or 1
    kliens.kuld(
        {
            "command": "turn",
            "angle_deg": irany * KERESES_FORDULAT_FOK,
            "max_angular_speed": TURN_SEBESSEG,
        }
    )
    stat.parancsok_szama += 1
    kereses_lepesek[0] += 1

    observe = kliens.kuld({"command": "observe"})
    stat.parancsok_szama += 1

    if not mindharom_nem_feher(observe):
        kereses_lepesek[0] = 0
        return Allapot.VONALON

    if kereses_lepesek[0] >= KERESES_MAX_LEPES:
        stat.palyaelhagyas = True

    return Allapot.KERESES


def futtat(host: str, port: int, max_lepes: int) -> FutasStatisztika:
    kliens = GatewayKliens(host, port)
    stat = FutasStatisztika()
    allapot = Allapot.VONALON
    utolso_elojel = [1]
    kereses_lepesek = [0]

    try:
        while stat.lepesek_szama < max_lepes and not stat.palyaelhagyas:
            if allapot is Allapot.VONALON:
                allapot = egy_lepes_vonalon(kliens, stat, utolso_elojel)
            else:
                allapot = egy_lepes_kereses(
                    kliens, stat, utolso_elojel, kereses_lepesek
                )
            stat.lepesek_szama += 1
    finally:
        kliens.close()

    return stat


def naplo_iras(stat: FutasStatisztika) -> None:
    NAPLO_FAJL.parent.mkdir(parents=True, exist_ok=True)
    bejegyzes = {
        "kezdet": stat.kezdet,
        "vege": datetime.now(timezone.utc).isoformat(),
        "lepesek_szama": stat.lepesek_szama,
        "parancsok_szama": stat.parancsok_szama,
        "vonalvesztesek_szama": stat.vonalvesztesek_szama,
        "palyaelhagyas": stat.palyaelhagyas,
    }
    with NAPLO_FAJL.open("a", encoding="utf-8") as f:
        json.dump(bejegyzes, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    print(f"Naplozva: {NAPLO_FAJL}")


def main() -> int:
    parser = argparse.ArgumentParser(description="M09 vonalkoveto baseline kontroller")
    parser.add_argument("--host", default=ALAPERTELMEZETT_HOST)
    parser.add_argument("--port", type=int, default=ALAPERTELMEZETT_PORT)
    parser.add_argument(
        "--max-lepes",
        type=int,
        default=500,
        help="Biztonsagi felso korlat a ciklusok szamara.",
    )
    args = parser.parse_args()

    print(f"Kapcsolodas: {args.host}:{args.port} ...")
    try:
        stat = futtat(args.host, args.port, args.max_lepes)
    except (ConnectionError, OSError) as hiba:
        print(f"Hiba: {hiba}", file=sys.stderr)
        return 1

    print(
        f"Futas vege: {stat.lepesek_szama} lepes, "
        f"{stat.parancsok_szama} parancs, "
        f"{stat.vonalvesztesek_szama} vonalveszes, "
        f"palyaelhagyas={stat.palyaelhagyas}"
    )
    naplo_iras(stat)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
