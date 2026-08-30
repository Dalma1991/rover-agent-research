#!/usr/bin/env python3
"""M11: egyszerű replay-vizualizáció a kiserlet_naplo.jsonl alapján.

Beolvas egy adott run_id-hoz tartozó futást a logs/kiserlet_naplo.jsonl
fájlból, és kirajzolja a pálya-nyomvonalat (a privilegizalt_diagnosztika
mezőben rögzített position adatból - kizárólag ez a szkript,
diagnosztikai/vizualizációs célra használja ezt, a kontroller maga
sosem), az állapot szerint színezve, az ütközéseket külön jelölve.

Ez a szkript nem "valódi" replay abban az értelemben, hogy nem küldi
újra a naplózott parancsokat a szimulátornak - csak a rögzített
pozíciókból rajzol egy 2D ábrát. Egy jövőbeli, teljes replay-eszköz
(ami ténylegesen visszajátssza a futást Unity Play módban) M11+
munkaként azonosítva.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


ALLAPOT_SZINEK = {
    "VONALON": "#2E86AB",
    "KERESES": "#A32D2D",
    "AKADALY": "#185FA5",
    "VISSZATALALAS": "#B8752E",
}


def betolt_futas(naplo_fajl: Path, run_id: str) -> list[dict]:
    sorok = []
    with naplo_fajl.open(encoding="utf-8") as f:
        for sor in f:
            sor = sor.strip()
            if not sor:
                continue
            bejegyzes = json.loads(sor)
            if bejegyzes.get("run_id", "").startswith(run_id):
                sorok.append(bejegyzes)
    return sorok


def legutolso_run_id(naplo_fajl: Path) -> str:
    utolso = None
    with naplo_fajl.open(encoding="utf-8") as f:
        for sor in f:
            sor = sor.strip()
            if sor:
                utolso = json.loads(sor)
    if utolso is None:
        raise ValueError("A naplófájl üres.")
    return utolso["run_id"]


def rajzol(sorok: list[dict], cim: str, kimeneti_fajl: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 8))

    for i in range(len(sorok) - 1):
        a = sorok[i]
        b = sorok[i + 1]
        poz_a = (a.get("privilegizalt_diagnosztika") or {}).get("position")
        poz_b = (b.get("privilegizalt_diagnosztika") or {}).get("position")
        if not poz_a or not poz_b:
            continue
        allapot = a.get("allapot_utana") or "VONALON"
        szin = ALLAPOT_SZINEK.get(allapot, "#888888")
        ax.plot(
            [poz_a["x"], poz_b["x"]], [poz_a["z"], poz_b["z"]],
            color=szin, linewidth=1.5,
        )

    # M11: a collision_occurred mezo "ragados" (igaz marad az elso
    # utkozes utan a teljes futas hatralevo reszere, lasd
    # RoverGatewayServer.cs: utkozesTortentAzUtolsoResetOta), ezert
    # az UJ utkozesek jelolesehez a collision_count NOVEKEDESET
    # hasznaljuk lepesenkent, nem a collision_occurred flaget onmagaban.
    utkozes_x, utkozes_z = [], []
    elozo_szamlalo = 0
    for sor in sorok:
        diag = sor.get("privilegizalt_diagnosztika") or {}
        szamlalo = diag.get("collision_count") or 0
        if szamlalo > elozo_szamlalo and diag.get("position"):
            utkozes_x.append(diag["position"]["x"])
            utkozes_z.append(diag["position"]["z"])
        elozo_szamlalo = szamlalo
    if utkozes_x:
        ax.scatter(utkozes_x, utkozes_z, color="black", marker="x", s=40, label="ütközés", zorder=5)

    for allapot, szin in ALLAPOT_SZINEK.items():
        ax.plot([], [], color=szin, label=allapot, linewidth=2)

    ax.set_xlabel("x (m)")
    ax.set_ylabel("z (m)")
    ax.set_title(cim)
    ax.legend(loc="upper right", fontsize=8)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)

    fig.savefig(kimeneti_fajl, dpi=150, bbox_inches="tight")
    print(f"Mentve: {kimeneti_fajl}")


def main() -> int:
    parser = argparse.ArgumentParser(description="M11 replay-vizualizáció")
    parser.add_argument(
        "--naplo-fajl",
        default=str(Path(__file__).resolve().parent.parent / "logs" / "kiserlet_naplo.jsonl"),
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="A vizualizálandó futás run_id-jának eleje. Ha nincs megadva, a naplófájl legutolsó futását használja.",
    )
    parser.add_argument(
        "--kimenet",
        default=None,
        help="A kimeneti kép útvonala. Alapértelmezetten logs/replay_<run_id>.png.",
    )
    args = parser.parse_args()

    naplo_fajl = Path(args.naplo_fajl)
    run_id = args.run_id or legutolso_run_id(naplo_fajl)
    sorok = betolt_futas(naplo_fajl, run_id)

    if not sorok:
        print(f"Nem található futás ehhez a run_id-hoz: {run_id}")
        return 1

    kimenet = Path(args.kimenet) if args.kimenet else naplo_fajl.parent / f"replay_{run_id[:8]}.png"
    controller = sorok[0].get("controller", "?")
    cim = f"Replay - {controller} - run {run_id[:8]} ({len(sorok)} lépés)"
    rajzol(sorok, cim, kimenet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())