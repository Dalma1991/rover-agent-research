#!/usr/bin/env python3
""""Hagyományos (AI nélküli) vonalkövető baseline kontroller - M09/M10/M10.5.
Állapotgép (VONALON / KERESÉS / AKADÁLY) + P-szabályozó a bal/jobb
szenzor intenzitáskülönbségére. A vezérlési döntések kizárólag az
observe válasz sensor_left/center/right és lidar_szektor_min
mezőire támaszkodnak, nem használják a position/speed/collision_*
privilegizált szimulátor-mezőket (ezek csak a lépésenkénti
diagnosztikai naplóba kerülnek, M10 bővítés - lásd docs/m10-plan.md).

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
LEPES_NAPLO_FAJL = (
    Path(__file__).resolve().parent.parent / "logs" / "m10_lepes_naplo.jsonl"
)

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

AKADALY_KUSZOB_BELEPES_M = 0.5
AKADALY_KUSZOB_KILEPES_M = 0.8
AKADALY_FORDULAT_FOK = 15.0
# M10: ha ennyi egymast koveto lepesig nem sikerul kikerulni az
# akadalyt (pl. ket akadaly koze szorult a rover - zsakutca), a
# tovabbi fordulgatas helyett a tagabb KERESES allapotra eszkalalunk.
ZSAKUTCA_AKADALY_MAX_LEPES = 20
ELOLSO_SZEKTOROK = (2, 3)
BAL_SZEKTOROK = (0, 1)
JOBB_SZEKTOROK = (4, 5)

# M10: explicit vonal-visszakeresés kerülés után (lásd docs/m10-plan.md,
# 4. munkacsomag). Rövid, IRÁNYÍTOTT keresés az elkerülő fordulattal
# ellentétes irányba (mivel a vonal feltehetően arra maradt) - ha ez
# VISSZATALALAS_MAX_LEPES lépésen belül nem talál vonalat, a rendszer
# átvált az általános, tágabb KERESÉS állapotra.
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
    # M10: a gateway collision_occurred/collision_count mezoibol szarmazik,
    # kizarolag diagnosztikai celra - a vezerlesi dontesekben nem hasznaljuk.
    utkozott: bool = False
    utkozesek_szama: int = 0
    kezdet: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class LepesNaplozo:
    """M10: lepesenkenti diagnosztikai naplo (JSONL).

    Minden lepesnel rogziti az allapotot, a nyers szenzor-/LiDAR-
    adatokat, a kiadott parancso(ka)t es - kizarolag diagnosztikai
    celra - a privilegizalt position/collision mezoket is, hogy az
    M09-ben dokumentalt oszcillacios jelenseg utolag elemezheto
    legyen (lasd docs/m10-plan.md). A vezerlo logika ezeket az
    adatokat nem hasznalja fel donteshez, csak a naplo kapja meg.
    """

    def __init__(self, fajl: Path, run_id: str) -> None:
        self.fajl = fajl
        self.run_id = run_id
        self.fajl.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.fajl.open("a", encoding="utf-8")

    def rogzit(
        self,
        lepes_szam: int,
        allapot_elotte: "Allapot",
        observe: dict[str, Any],
        parancsok: list[dict[str, Any]],
        allapot_utana: "Allapot",
    ) -> None:
        bejegyzes = {
            "run_id": self.run_id,
            "idobelyeg": datetime.now(timezone.utc).isoformat(),
            "lepes_szam": lepes_szam,
            "allapot_elotte": allapot_elotte.value,
            "allapot_utana": allapot_utana.value,
            "sensor_left": observe.get("sensor_left"),
            "sensor_center": observe.get("sensor_center"),
            "sensor_right": observe.get("sensor_right"),
            "lidar_szektor_min": observe.get("lidar_szektor_min"),
            "parancsok": parancsok,
            # Kizarolag diagnosztikai celra (lasd docstring):
            "position": observe.get("position"),
            "collision_occurred": observe.get("collision_occurred"),
            "collision_count": observe.get("collision_count"),
        }
        json.dump(bejegyzes, self._fh, ensure_ascii=False, separators=(",", ":"))
        self._fh.write("\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()


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


def akadaly_elol(observe_valasz: dict[str, Any], kuszob: float) -> bool:
    """Igazat ad vissza, ha az elulso szektorok barmelyikeben a legkozelebbi
    akadaly a megadott kuszob tavolsagon belul van. Hianyzo/ures
    lidar_szektor_min eseten ovatosan False-t ad vissza (nincs eszleles).

    Ket kulonbozo kuszobbel hivjuk (hiszterezis): AKADALY_KUSZOB_BELEPES_M
    (szukebb, VONALON -> AKADALY valtashoz) es AKADALY_KUSZOB_KILEPES_M
    (tagabb, AKADALY -> VONALON valtashoz), hogy a hatarertek kozeli
    oszcillaciot elkeruljuk."""
    szektorok = observe_valasz.get("lidar_szektor_min") or []
    if len(szektorok) <= max(ELOLSO_SZEKTOROK):
        return False
    return any(szektorok[i] < kuszob for i in ELOLSO_SZEKTOROK)


def szabadabb_oldal_elojele(observe_valasz: dict[str, Any]) -> int:
    """1, ha jobbra van tobb hely (tehat jobbra kell fordulni), -1 ha balra."""
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
    naplo: LepesNaplozo | None,
    lepes_szam: int,
) -> Allapot:
    observe = kliens.kuld({"command": "observe"})
    stat.parancsok_szama += 1
    kiadott_parancsok: list[dict[str, Any]] = []

    if akadaly_elol(observe, AKADALY_KUSZOB_BELEPES_M):
        stat.akadaly_kerulesek_szama += 1
        if naplo is not None:
            naplo.rogzit(lepes_szam, Allapot.VONALON, observe, kiadott_parancsok, Allapot.AKADALY)
        return Allapot.AKADALY

    if mindharom_nem_feher(observe):
        stat.vonalvesztesek_szama += 1
        if naplo is not None:
            naplo.rogzit(lepes_szam, Allapot.VONALON, observe, kiadott_parancsok, Allapot.KERESES)
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
        naplo.rogzit(lepes_szam, Allapot.VONALON, observe, kiadott_parancsok, Allapot.VONALON)
    return Allapot.VONALON


def egy_lepes_akadaly(
    kliens: GatewayKliens,
    stat: FutasStatisztika,
    utolso_elkerulesi_irany: list[int],
    akadaly_lepesek: list[int],
    naplo: LepesNaplozo | None,
    lepes_szam: int,
) -> Allapot:
    observe = kliens.kuld({"command": "observe"})
    stat.parancsok_szama += 1

    if not akadaly_elol(observe, AKADALY_KUSZOB_KILEPES_M):
        # M10: nem közvetlenül VONALON-ra váltunk, hanem egy rövid,
        # irányított visszakeresésre - lásd egy_lepes_visszatalalas().
        # Ez az ág akkor is aktiválódik, ha az akadály közben eltűnt
        # (schedule.disappear_at_s) - a rover a rendelkezésére álló,
        # nem-privilegizált adatokból (LiDAR) nem tudja megkülönböztetni
        # ezt a sikeres kerüléstől; ez a különbség utólag, diagnosztikai
        # célra a lépésnaplóból (position mező) állapítható meg, lásd
        # analyze_step_log.py. Tudatosan nem próbáljuk ezt valós időben
        # megkülönböztetni, mert az privilegizált adat használatát
        # igényelné a vezérlési döntésben.
        akadaly_lepesek[0] = 0
        if naplo is not None:
            naplo.rogzit(lepes_szam, Allapot.AKADALY, observe, [], Allapot.VISSZATALALAS)
        return Allapot.VISSZATALALAS

    akadaly_lepesek[0] += 1
    if akadaly_lepesek[0] >= ZSAKUTCA_AKADALY_MAX_LEPES:
        # M10: zsákutca-észlelés - a további fordulgatás helyett a
        # tágabb KERESÉS állapotra eszkalálunk, és külön számláljuk
        # zsákutca-esetként a hiba-taxonómia számára.
        akadaly_lepesek[0] = 0
        stat.zsakutcak_szama += 1
        if naplo is not None:
            naplo.rogzit(lepes_szam, Allapot.AKADALY, observe, [], Allapot.KERESES)
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

    # M10.5: az AKADALY allapot korabban csak fordult, sosem haladt elore -
    # ez okozta a dokumentalt AKADALY<->VISSZATALALAS oszcillaciot (lasd
    # docs/m10-5-plan.md). A javitas: forgatas utan mindig elore is haladunk,
    # hogy tenyleges oldaltavolsagot nyerjunk az akadalytol. (Egy korabbi
    # kiserlet, ami ezt egy biztonsagos-tavolsag feltetelhez kototte,
    # rontott az eredmenyen - lasd m10-5-plan.md, elvetve.)
    move_parancs = {
        "command": "move", "distance_m": MOVE_LEPES_M, "max_speed": MOVE_SEBESSEG
    }
    kliens.kuld(move_parancs)
    stat.parancsok_szama += 1
    kiadott_parancsok.append(move_parancs)

    if naplo is not None:
        naplo.rogzit(lepes_szam, Allapot.AKADALY, observe, kiadott_parancsok, Allapot.AKADALY)
    return Allapot.AKADALY

def egy_lepes_visszatalalas(
    kliens: GatewayKliens,
    stat: FutasStatisztika,
    utolso_elkerulesi_irany: list[int],
    visszatalalas_lepesek: list[int],
    naplo: LepesNaplozo | None,
    lepes_szam: int,
) -> Allapot:
    """M10: explicit, iranyitott vonal-visszakereses akadalykerules utan.

    Feltetelezes (meg nem validalt): mivel az AKADALY allapotban a
    szabadabb oldal fele fordultunk el, a vonal valoszinuleg az azzal
    ELLENTETES iranyban maradt. Ezert kis lepesekkel visszafordulunk
    arra, es kozben elore haladunk, amig valamelyik szenzor 'white'-ot
    nem jelez, vagy el nem erjuk a VISSZATALALAS_MAX_LEPES korlatot -
    ekkor a tagabb, altalanos KERESES allapotra eszkalalunk.
    """
    observe = kliens.kuld({"command": "observe"})
    stat.parancsok_szama += 1
    kiadott_parancsok: list[dict[str, Any]] = []

    if not mindharom_nem_feher(observe):
        visszatalalas_lepesek[0] = 0
        if naplo is not None:
            naplo.rogzit(lepes_szam, Allapot.VISSZATALALAS, observe, kiadott_parancsok, Allapot.VONALON)
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
            naplo.rogzit(lepes_szam, Allapot.VISSZATALALAS, observe2, kiadott_parancsok, Allapot.VONALON)
        return Allapot.VONALON

    if visszatalalas_lepesek[0] >= VISSZATALALAS_MAX_LEPES:
        visszatalalas_lepesek[0] = 0
        stat.vonalvesztesek_szama += 1
        if naplo is not None:
            naplo.rogzit(lepes_szam, Allapot.VISSZATALALAS, observe2, kiadott_parancsok, Allapot.KERESES)
        return Allapot.KERESES

    if naplo is not None:
        naplo.rogzit(lepes_szam, Allapot.VISSZATALALAS, observe2, kiadott_parancsok, Allapot.VISSZATALALAS)
    return Allapot.VISSZATALALAS


def egy_lepes_kereses(
    kliens: GatewayKliens,
    stat: FutasStatisztika,
    utolso_elojel: list[int],
    kereses_lepesek: list[int],
    naplo: LepesNaplozo | None,
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
            naplo.rogzit(lepes_szam, Allapot.KERESES, observe, [turn_parancs], Allapot.VONALON)
        return Allapot.VONALON

    if kereses_lepesek[0] >= KERESES_MAX_LEPES:
        stat.palyaelhagyas = True

    if naplo is not None:
        naplo.rogzit(lepes_szam, Allapot.KERESES, observe, [turn_parancs], Allapot.KERESES)
    return Allapot.KERESES


def futtat(
    host: str, port: int, max_lepes: int, lepes_naplo_fajl: Path | None = LEPES_NAPLO_FAJL
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
    naplo = LepesNaplozo(lepes_naplo_fajl, run_id) if lepes_naplo_fajl else None

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

        # M10: futas vegi observe kizarolag az utkozes-osszegzeshez -
        # ez maga nem befolyasolja a mar meghozott vezerlesi dontest.
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
        "--lepes-naplo",
        default=str(LEPES_NAPLO_FAJL),
        help=(
            "Lepesenkenti diagnosztikai naplo (JSONL) utvonala. "
            "Ures string (--lepes-naplo '') eseten kikapcsolja."
        ),
    )
    args = parser.parse_args()
    lepes_naplo_fajl = Path(args.lepes_naplo) if args.lepes_naplo else None

    print(f"Kapcsolodas: {args.host}:{args.port} ...")
    try:
        stat = futtat(args.host, args.port, args.max_lepes, lepes_naplo_fajl)
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