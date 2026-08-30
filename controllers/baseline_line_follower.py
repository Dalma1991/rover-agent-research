#!/usr/bin/env python3
"""Hagyományos (AI nélküli) vonalkövető baseline kontroller - M09/M10/M10.5/M11.

Állapotgép (VONALON / KERESÉS / AKADÁLY) + P-szabályozó a bal/jobb
szenzor intenzitáskülönbségére. A vezérlési döntések kizárólag az
observe válasz sensor_left/center/right és lidar_szektor_min
mezőire támaszkodnak, nem használják a position/speed/collision_*
privilegizált szimulátor-mezőket (ezek csak a lépésenkénti
diagnosztikai naplóba kerülnek).

M11: a lépésenkénti naplózás mostantól a common.kiserlet_naplo
egységes modulját használja (KiserletNaplozo), ami minden jelenlegi
és jövőbeli kontroller (baseline, agent-alapú, tanult) számára közös
séma szerint ír JSONL naplót a logs/kiserlet_naplo.jsonl fájlba.

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

_PROJEKT_GYOKER = str(Path(__file__).resolve().parent.parent)
if _PROJEKT_GYOKER not in sys.path:
    sys.path.insert(0, _PROJEKT_GYOKER)

from common.kiserlet_naplo import KiserletMetaadat, KiserletNaplozo


ALAPERTELMEZETT_HOST = "127.0.0.1"
ALAPERTELMEZETT_PORT = 8765
MAXIMALIS_FRAME_MERET = 16 * 1024
NAPLO_FAJL = Path(__file__).resolve().parent.parent / "logs" / "m09_runs.jsonl"
KISERLET_NAPLO_FAJL = (
    Path(__file__).resolve().parent.parent / "logs" / "kiserlet_naplo.jsonl"
)
CONTROLLER_NEV = "baseline_line_follower"
BACKEND_NEV = "unity_sim"

MOVE_LEPES_M = 0.08
MOVE_SEBESSEG = 0.20
TURN_MIN_FOK = 1.0
TURN_MAX_FOK = 5.0
TURN_SEBESSEG = 20.0
P_EROSITES = 8.0
HOLTSAV = 0.02

KERESES_FORDULAT_FOK = 3.0
KERESES_MAX_LEPES = 40

AKADALY_KUSZOB_BELEPES_M = 0.5
AKADALY_KUSZOB_KILEPES_M = 1.1
AKADALY_FORDULAT_FOK = 15.0
ZSAKUTCA_AKADALY_MAX_LEPES = 20
ELOLSO_SZEKTOROK = (2, 3)
BAL_SZEKTOROK = (0, 1)
JOBB_SZEKTOROK = (4, 5)

VISSZATALALAS_FORDULAT_FOK = 5.0
VISSZATALALAS_MAX_LEPES = 15


class Allapot(Enum):
    VONALON = "VONALON"
    KERESES = "KERESES"
    AKADALY = "AKADALY"
    VISSZATALALAS = "VISSZATALALAS"


@dataclass
class FutasStatisztika:
    lepesek_szama: int = 0
    parancsok_szama: int = 0
    vonalvesztesek_szama: int = 0
    akadaly_kerulesek_szama: int = 0
    zsakutcak_szama: int = 0
    palyaelhagyas: bool = False
    utkozott: bool = False
    utkozesek_szama: int = 0
    kezdet: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def szenzor_mezok(observe: dict[str, Any]) -> dict[str, Any]:
    return {
        "sensor_left": observe.get("sensor_left"),
        "sensor_center": observe.get("sensor_center"),
        "sensor_right": observe.get("sensor_right"),
        "lidar_szektor_min": observe.get("lidar_szektor_min"),
    }


def privilegizalt_diagnosztika_mezok(observe: dict[str, Any]) -> dict[str, Any]:
    return {
        "position": observe.get("position"),
        "collision_occurred": observe.get("collision_occurred"),
        "collision_count": observe.get("collision_count"),
    }


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
    bal = observe_valasz["sensor_left"]["intensity"]
    jobb = observe_valasz["sensor_right"]["intensity"]
    return jobb - bal


def mindharom_nem_feher(observe_valasz: dict[str, Any]) -> bool:
    return not (
        observe_valasz["sensor_left"]["white"]
        or observe_valasz["sensor_center"]["white"]
        or observe_valasz["sensor_right"]["white"]
    )


def akadaly_elol(observe_valasz: dict[str, Any], kuszob: float) -> bool:
    szektorok = observe_valasz.get("lidar_szektor_min") or []
    if len(szektorok) <= max(ELOLSO_SZEKTOROK):
        return False
    return any(szektorok[i] < kuszob for i in ELOLSO_SZEKTOROK)


def szabadabb_oldal_elojele(observe_valasz: dict[str, Any]) -> int:
    szektorok = observe_valasz.get("lidar_szektor_min") or []
    if len(szektorok) <= max(JOBB_SZEKTOROK):
        return 1
    bal_min = min(szektorok[i] for i in BAL_SZEKTOROK)
    jobb_min = min(szektorok[i] for i in JOBB_SZEKTOROK)
    return 1 if jobb_min >= bal_min else -1


def egy_lepes_vonalon(
    kliens: GatewayKliens,
    stat: FutasStatisztika,
    utolso_elojel: list[int],
    naplo: KiserletNaplozo | None,
    lepes_szam: int,
) -> Allapot:
    observe = kliens.kuld({"command": "observe"})
    stat.parancsok_szama += 1
    kiadott_parancsok: list[dict[str, Any]] = []

    if akadaly_elol(observe, AKADALY_KUSZOB_BELEPES_M):
        stat.akadaly_kerulesek_szama += 1
        if naplo is not None:
            naplo.rogzit(lepes_szam, szenzor_mezok(observe), kiadott_parancsok, Allapot.VONALON.value, Allapot.AKADALY.value, privilegizalt_diagnosztika_mezok(observe))
        return Allapot.AKADALY

    if mindharom_nem_feher(observe):
        stat.vonalvesztesek_szama += 1
        if naplo is not None:
            naplo.rogzit(lepes_szam, szenzor_mezok(observe), kiadott_parancsok, Allapot.VONALON.value, Allapot.KERESES.value, privilegizalt_diagnosztika_mezok(observe))
        return Allapot.KERESES

    hiba = hibajel_szamitasa(observe)
    if abs(hiba) > HOLTSAV:
        utolso_elojel[0] = 1 if hiba > 0 else -1
        korrekcio_fok = max(TURN_MIN_FOK, min(TURN_MAX_FOK, abs(hiba) * P_EROSITES))
        szog = korrekcio_fok if hiba > 0 else -korrekcio_fok
        turn_parancs = {
            "command": "turn", "angle_deg": szog, "max_angular_speed": TURN_SEBESSEG
        }
        kliens.kuld(turn_parancs)
        stat.parancsok_szama += 1
        kiadott_parancsok.append(turn_parancs)

    move_parancs = {
        "command": "move", "distance_m": MOVE_LEPES_M, "max_speed": MOVE_SEBESSEG
    }
    kliens.kuld(move_parancs)
    stat.parancsok_szama += 1
    kiadott_parancsok.append(move_parancs)
    if naplo is not None:
        naplo.rogzit(lepes_szam, szenzor_mezok(observe), kiadott_parancsok, Allapot.VONALON.value, Allapot.VONALON.value, privilegizalt_diagnosztika_mezok(observe))
    return Allapot.VONALON


def egy_lepes_akadaly(
    kliens: GatewayKliens,
    stat: FutasStatisztika,
    utolso_elkerulesi_irany: list[int],
    akadaly_lepesek: list[int],
    naplo: KiserletNaplozo | None,
    lepes_szam: int,
) -> Allapot:
    observe = kliens.kuld({"command": "observe"})
    stat.parancsok_szama += 1

    if not akadaly_elol(observe, AKADALY_KUSZOB_KILEPES_M):
        akadaly_lepesek[0] = 0
        if naplo is not None:
            naplo.rogzit(lepes_szam, szenzor_mezok(observe), [], Allapot.AKADALY.value, Allapot.VISSZATALALAS.value, privilegizalt_diagnosztika_mezok(observe))
        return Allapot.VISSZATALALAS

    akadaly_lepesek[0] += 1
    if akadaly_lepesek[0] >= ZSAKUTCA_AKADALY_MAX_LEPES:
        akadaly_lepesek[0] = 0
        stat.zsakutcak_szama += 1
        if naplo is not None:
            naplo.rogzit(lepes_szam, szenzor_mezok(observe), [], Allapot.AKADALY.value, Allapot.KERESES.value, privilegizalt_diagnosztika_mezok(observe))
        return Allapot.KERESES

    irany = szabadabb_oldal_elojele(observe)
    utolso_elkerulesi_irany[0] = irany
    turn_parancs = {
        "command": "turn",
        "angle_deg": irany * AKADALY_FORDULAT_FOK,
        "max_angular_speed": TURN_SEBESSEG,
    }
    kliens.kuld(turn_parancs)
    stat.parancsok_szama += 1
    kiadott_parancsok: list[dict[str, Any]] = [turn_parancs]

    move_parancs = {
        "command": "move", "distance_m": MOVE_LEPES_M, "max_speed": MOVE_SEBESSEG
    }
    kliens.kuld(move_parancs)
    stat.parancsok_szama += 1
    kiadott_parancsok.append(move_parancs)

    if naplo is not None:
        naplo.rogzit(lepes_szam, szenzor_mezok(observe), kiadott_parancsok, Allapot.AKADALY.value, Allapot.AKADALY.value, privilegizalt_diagnosztika_mezok(observe))
    return Allapot.AKADALY


def egy_lepes_visszatalalas(
    kliens: GatewayKliens,
    stat: FutasStatisztika,
    utolso_elkerulesi_irany: list[int],
    visszatalalas_lepesek: list[int],
    naplo: KiserletNaplozo | None,
    lepes_szam: int,
) -> Allapot:
    observe = kliens.kuld({"command": "observe"})
    stat.parancsok_szama += 1
    kiadott_parancsok: list[dict[str, Any]] = []

    if not mindharom_nem_feher(observe):
        visszatalalas_lepesek[0] = 0
        if naplo is not None:
            naplo.rogzit(lepes_szam, szenzor_mezok(observe), kiadott_parancsok, Allapot.VISSZATALALAS.value, Allapot.VONALON.value, privilegizalt_diagnosztika_mezok(observe))
        return Allapot.VONALON

    irany_vissza = -utolso_elkerulesi_irany[0]
    turn_parancs = {
        "command": "turn",
        "angle_deg": irany_vissza * VISSZATALALAS_FORDULAT_FOK,
        "max_angular_speed": TURN_SEBESSEG,
    }
    kliens.kuld(turn_parancs)
    stat.parancsok_szama += 1
    kiadott_parancsok.append(turn_parancs)

    move_parancs = {
        "command": "move", "distance_m": MOVE_LEPES_M, "max_speed": MOVE_SEBESSEG
    }
    kliens.kuld(move_parancs)
    stat.parancsok_szama += 1
    kiadott_parancsok.append(move_parancs)
    visszatalalas_lepesek[0] += 1

    observe2 = kliens.kuld({"command": "observe"})
    stat.parancsok_szama += 1

    if not mindharom_nem_feher(observe2):
        visszatalalas_lepesek[0] = 0
        if naplo is not None:
            naplo.rogzit(lepes_szam, szenzor_mezok(observe2), kiadott_parancsok, Allapot.VISSZATALALAS.value, Allapot.VONALON.value, privilegizalt_diagnosztika_mezok(observe2))
        return Allapot.VONALON

    if visszatalalas_lepesek[0] >= VISSZATALALAS_MAX_LEPES:
        visszatalalas_lepesek[0] = 0
        stat.vonalvesztesek_szama += 1
        if naplo is not None:
            naplo.rogzit(lepes_szam, szenzor_mezok(observe2), kiadott_parancsok, Allapot.VISSZATALALAS.value, Allapot.KERESES.value, privilegizalt_diagnosztika_mezok(observe2))
        return Allapot.KERESES

    if naplo is not None:
        naplo.rogzit(lepes_szam, szenzor_mezok(observe2), kiadott_parancsok, Allapot.VISSZATALALAS.value, Allapot.VISSZATALALAS.value, privilegizalt_diagnosztika_mezok(observe2))
    return Allapot.VISSZATALALAS


def egy_lepes_kereses(
    kliens: GatewayKliens,
    stat: FutasStatisztika,
    utolso_elojel: list[int],
    kereses_lepesek: list[int],
    naplo: KiserletNaplozo | None,
    lepes_szam: int,
) -> Allapot:
    irany = utolso_elojel[0] or 1
    turn_parancs = {
        "command": "turn",
        "angle_deg": irany * KERESES_FORDULAT_FOK,
        "max_angular_speed": TURN_SEBESSEG,
    }
    kliens.kuld(turn_parancs)
    stat.parancsok_szama += 1
    kereses_lepesek[0] += 1

    observe = kliens.kuld({"command": "observe"})
    stat.parancsok_szama += 1

    if not mindharom_nem_feher(observe):
        kereses_lepesek[0] = 0
        if naplo is not None:
            naplo.rogzit(lepes_szam, szenzor_mezok(observe), [turn_parancs], Allapot.KERESES.value, Allapot.VONALON.value, privilegizalt_diagnosztika_mezok(observe))
        return Allapot.VONALON

    if kereses_lepesek[0] >= KERESES_MAX_LEPES:
        stat.palyaelhagyas = True

    if naplo is not None:
        naplo.rogzit(lepes_szam, szenzor_mezok(observe), [turn_parancs], Allapot.KERESES.value, Allapot.KERESES.value, privilegizalt_diagnosztika_mezok(observe))
    return Allapot.KERESES


def futtat(
    host: str, port: int, max_lepes: int, kiserlet_naplo_fajl: Path | None = KISERLET_NAPLO_FAJL, seed: int | None = None
) -> FutasStatisztika:
    kliens = GatewayKliens(host, port)
    stat = FutasStatisztika()
    allapot = Allapot.VONALON
    utolso_elojel = [1]
    kereses_lepesek = [0]
    utolso_elkerulesi_irany = [1]
    visszatalalas_lepesek = [0]
    akadaly_lepesek = [0]
    run_id = str(uuid4())
    naplo = (
        KiserletNaplozo(
            kiserlet_naplo_fajl,
            run_id,
            KiserletMetaadat(controller=CONTROLLER_NEV, backend=BACKEND_NEV, seed=seed),
        )
        if kiserlet_naplo_fajl
        else None
    )

    try:
        kliens.kuld({"command": "reset_position"})

        while stat.lepesek_szama < max_lepes and not stat.palyaelhagyas:
            if allapot is Allapot.VONALON:
                allapot = egy_lepes_vonalon(
                    kliens, stat, utolso_elojel, naplo, stat.lepesek_szama
                )
            elif allapot is Allapot.AKADALY:
                allapot = egy_lepes_akadaly(
                    kliens, stat, utolso_elkerulesi_irany, akadaly_lepesek, naplo, stat.lepesek_szama
                )
            elif allapot is Allapot.VISSZATALALAS:
                allapot = egy_lepes_visszatalalas(
                    kliens,
                    stat,
                    utolso_elkerulesi_irany,
                    visszatalalas_lepesek,
                    naplo,
                    stat.lepesek_szama,
                )
            else:
                allapot = egy_lepes_kereses(
                    kliens, stat, utolso_elojel, kereses_lepesek, naplo, stat.lepesek_szama
                )
            stat.lepesek_szama += 1

        vegso_observe = kliens.kuld({"command": "observe"})
        stat.parancsok_szama += 1
        stat.utkozott = bool(vegso_observe.get("collision_occurred", False))
        stat.utkozesek_szama = int(vegso_observe.get("collision_count", 0) or 0)
    finally:
        if naplo is not None:
            naplo.close()
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
        "akadaly_kerulesek_szama": stat.akadaly_kerulesek_szama,
        "zsakutcak_szama": stat.zsakutcak_szama,
        "palyaelhagyas": stat.palyaelhagyas,
        "utkozott": stat.utkozott,
        "utkozesek_szama": stat.utkozesek_szama,
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
    parser.add_argument(
        "--kiserlet-naplo",
        default=str(KISERLET_NAPLO_FAJL),
        help=(
            "M11: egyseges kiserlet-naplo (JSONL) utvonala. "
            "Ures string (--kiserlet-naplo '') eseten kikapcsolja."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="A hasznalt szcenario seed-je, kizarolag naplozasi celra.",
    )
    args = parser.parse_args()
    kiserlet_naplo_fajl = Path(args.kiserlet_naplo) if args.kiserlet_naplo else None

    print(f"Kapcsolodas: {args.host}:{args.port} ...")
    try:
        stat = futtat(args.host, args.port, args.max_lepes, kiserlet_naplo_fajl, args.seed)
    except (ConnectionError, OSError) as hiba:
        print(f"Hiba: {hiba}", file=sys.stderr)
        return 1

    print(
        f"Futas vege: {stat.lepesek_szama} lepes, "
        f"{stat.parancsok_szama} parancs, "
        f"{stat.vonalvesztesek_szama} vonalveszes, "
        f"{stat.akadaly_kerulesek_szama} akadalykerules, "
        f"zsakutcak={stat.zsakutcak_szama}, "
        f"utkozesek={stat.utkozesek_szama}, "
        f"palyaelhagyas={stat.palyaelhagyas}"
    )
    naplo_iras(stat)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())