#!/usr/bin/env python3
"""M11: egyszerű replay-vizualizáció a kiserlet_naplo.jsonl alapján.

Beolvas egy adott run_id-hoz tartozó futást a logs/kiserlet_naplo.jsonl
fájlból, és kirajzolja a pálya-nyomvonalat (a privilegizalt_diagnosztika
mezőben rögzített position adatból - kizárólag ez a szkript,
diagnosztikai/vizualizációs célra használja ezt, a kontroller maga
sosem), az állapot szerint színezve, az ütközéseket külön jelölve.

Ez a szkript nem "valódi" replay abban az értelemben, hogy nem küldi
újra a naplózott parancsokat a szimulátornak - csak a rögzített
pozíciókból rajzol egy 2D ábrát. A --video kapcsolóval
animált változat is készül (a nyomvonal lépésről lépésre épül fel,
a rover pozíciója és állapota képkockánként látszik). Egy jövőbeli,
teljes replay-eszköz (ami ténylegesen visszajátssza a naplózott
parancsokat Unity Play módban) M12+ munkaként azonosítva.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import animation


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


def _szakaszok(sorok: list[dict]) -> list[tuple[float, float, float, float, str]]:
    """(x_a, z_a, x_b, z_b, allapot) szakaszok az egymast koveto lepesekbol."""
    ki = []
    for i in range(len(sorok) - 1):
        poz_a = (sorok[i].get("privilegizalt_diagnosztika") or {}).get("position")
        poz_b = (sorok[i + 1].get("privilegizalt_diagnosztika") or {}).get("position")
        if not poz_a or not poz_b:
            continue
        allapot = sorok[i].get("allapot_utana") or "VONALON"
        ki.append((poz_a["x"], poz_a["z"], poz_b["x"], poz_b["z"], allapot))
    return ki


def _utkozes_pontok(sorok: list[dict]) -> list[tuple[int, float, float]]:
    """(lepes_index, x, z) minden UJ utkozesnel (collision_count novekmeny)."""
    ki = []
    elozo = 0
    for i, sor in enumerate(sorok):
        diag = sor.get("privilegizalt_diagnosztika") or {}
        szamlalo = diag.get("collision_count") or 0
        if szamlalo > elozo and diag.get("position"):
            ki.append((i, diag["position"]["x"], diag["position"]["z"]))
        elozo = szamlalo
    return ki


def video(
    sorok: list[dict], cim: str, kimeneti_fajl: Path, fps: int = 20, lepes_per_kepkocka: int = 2
) -> None:
    """Animalt replay: a nyomvonal lepesrol lepesre epul fel, a rover
    aktualis pozicioja es allapota kepkockankent frissul. GIF-be ment
    (Pillow iro, nem igenyel ffmpeg-et); .mp4 kiterjesztesnel ffmpeg-et
    hasznal, ha elerheto."""
    szakaszok = _szakaszok(sorok)
    utkozesek = _utkozes_pontok(sorok)
    if not szakaszok:
        raise ValueError("Nincs pozicioadat a naploban, video nem keszitheto.")

    xs = [s[0] for s in szakaszok] + [szakaszok[-1][2]]
    zs = [s[1] for s in szakaszok] + [szakaszok[-1][3]]
    margo = 0.5

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_xlim(min(xs) - margo, max(xs) + margo)
    ax.set_ylim(min(zs) - margo, max(zs) + margo)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("z (m)")
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    for allapot, szin in ALLAPOT_SZINEK.items():
        ax.plot([], [], color=szin, label=allapot, linewidth=2)
    ax.scatter([], [], color="black", marker="x", s=40, label="ütközés")
    ax.legend(loc="upper right", fontsize=8)

    (rover_pont,) = ax.plot([], [], "o", color="black", markersize=8, zorder=6)
    utkozes_scatter = ax.scatter([], [], color="black", marker="x", s=40, zorder=5)
    cim_szoveg = ax.set_title(cim)

    kepkockak = list(range(0, len(szakaszok) + 1, lepes_per_kepkocka))
    if kepkockak[-1] != len(szakaszok):
        kepkockak.append(len(szakaszok))
    rajzolt = 0

    def frissit(n: int):
        nonlocal rajzolt
        for j in range(rajzolt, n):
            xa, za, xb, zb, allapot = szakaszok[j]
            ax.plot([xa, xb], [za, zb], color=ALLAPOT_SZINEK.get(allapot, "#888888"), linewidth=1.5)
        rajzolt = n
        if n > 0:
            xa, za, xb, zb, allapot = szakaszok[n - 1]
            rover_pont.set_data([xb], [zb])
        else:
            allapot = szakaszok[0][4]
            rover_pont.set_data([szakaszok[0][0]], [szakaszok[0][1]])
        eddigi = [(x, z) for (i, x, z) in utkozesek if i <= n]
        utkozes_scatter.set_offsets(eddigi if eddigi else [[float("nan"), float("nan")]])
        cim_szoveg.set_text(
            f"{cim}\nlépés {n}/{len(szakaszok)} - {allapot} - ütközés: {len(eddigi)}"
        )
        return rover_pont, utkozes_scatter, cim_szoveg

    anim = animation.FuncAnimation(
        fig, frissit, frames=kepkockak, interval=1000 / fps, blit=False, repeat=False
    )

    kimeneti_fajl.parent.mkdir(parents=True, exist_ok=True)
    if kimeneti_fajl.suffix.lower() == ".mp4" and animation.writers.is_available("ffmpeg"):
        anim.save(str(kimeneti_fajl), writer=animation.FFMpegWriter(fps=fps, bitrate=1800))
    else:
        if kimeneti_fajl.suffix.lower() != ".gif":
            kimeneti_fajl = kimeneti_fajl.with_suffix(".gif")
        anim.save(str(kimeneti_fajl), writer=animation.PillowWriter(fps=fps))
    plt.close(fig)
    print(f"Video mentve: {kimeneti_fajl} ({len(kepkockak)} képkocka, {fps} fps)")


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
            [poz_a["x"], poz_b["x"]],
            [poz_a["z"], poz_b["z"]],
            color=szin,
            linewidth=1.5,
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
    parser.add_argument(
        "--video",
        default=None,
        help="Animált replay mentése ide (.gif Pillow-val, .mp4 ffmpeg-gel ha elérhető). Ha nincs megadva, csak a statikus kép készül.",
    )
    parser.add_argument(
        "--fps", type=int, default=20, help="Videó képkockasebessége (alapértelmezett: 20)."
    )
    parser.add_argument(
        "--lepes-per-kepkocka",
        type=int,
        default=2,
        help="Hány naplózott lépés kerüljön egy képkockába (alapértelmezett: 2).",
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
    if args.video:
        video(
            sorok, cim, Path(args.video), fps=args.fps, lepes_per_kepkocka=args.lepes_per_kepkocka
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
