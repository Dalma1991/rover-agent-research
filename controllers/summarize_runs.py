#!/usr/bin/env python3
"""Osszegzo statisztika az M09/M10 baseline kontroller futasi naploibol.

Megjegyzes: az "utkozott"/"utkozesek_szama" mezok csak az M10 bovites
(RoverGatewayServer collision_occurred/collision_count) utan keszult
naplobejegyzesekben szerepelnek - regebbi (M09) sorokban hianyozhatnak,
ezert ezekre .get(..., alapertelmezett) hasznalatos.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

NAPLO_FAJL = Path(__file__).resolve().parent.parent / "logs" / "m09_runs.jsonl"


def utolso_n_futas(n: int) -> list[dict]:
    sorok = NAPLO_FAJL.read_text(encoding="utf-8").strip().split("\n")
    utolsok = sorok[-n:]
    return [json.loads(sor) for sor in utolsok]


def osszegez(n: int = 30) -> None:
    futasok = utolso_n_futas(n)

    parancsok = [f["parancsok_szama"] for f in futasok]
    vonalveszesek = [f["vonalvesztesek_szama"] for f in futasok]
    akadalykerulesek = [f["akadaly_kerulesek_szama"] for f in futasok]
    zsakutcak = [f.get("zsakutcak_szama", 0) for f in futasok]
    palyaelhagyasok = sum(1 for f in futasok if f["palyaelhagyas"])
    utkozesek = [f.get("utkozesek_szama", 0) for f in futasok]
    utkozott_futasok = sum(1 for f in futasok if f.get("utkozott", False))

    print(f"Osszegzes ({len(futasok)} futas):")
    print(
        f"  Parancsok szama:      atlag={statistics.mean(parancsok):.1f}, "
        f"szoras={statistics.stdev(parancsok):.1f}, "
        f"min={min(parancsok)}, max={max(parancsok)}"
    )
    print(
        f"  Vonalvesztesek szama: atlag={statistics.mean(vonalveszesek):.1f}, "
        f"szoras={statistics.stdev(vonalveszesek):.1f}, "
        f"min={min(vonalveszesek)}, max={max(vonalveszesek)}"
    )
    print(
        f"  Akadalykerulesek:     atlag={statistics.mean(akadalykerulesek):.1f}, "
        f"szoras={statistics.stdev(akadalykerulesek):.1f}, "
        f"min={min(akadalykerulesek)}, max={max(akadalykerulesek)}"
    )
    print(
        f"  Zsakutcak szama:      atlag={statistics.mean(zsakutcak):.1f}, "
        f"szoras={statistics.stdev(zsakutcak):.1f}, "
        f"min={min(zsakutcak)}, max={max(zsakutcak)}"
    )
    print(f"  Palyaelhagyasok:      {palyaelhagyasok}/{len(futasok)} futasban")
    print(
        f"  Utkozesek szama:      atlag={statistics.mean(utkozesek):.1f}, "
        f"szoras={statistics.stdev(utkozesek):.1f}, "
        f"min={min(utkozesek)}, max={max(utkozesek)}"
    )
    print(f"  Utkozott futasok:     {utkozott_futasok}/{len(futasok)} futasban")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Baseline futasi naplok osszegzese")
    parser.add_argument(
        "--utolso",
        type=int,
        default=30,
        help="Hany legutobbi futast osszegezzen a naplobol (alapertelmezett: 30).",
    )
    args = parser.parse_args()
    osszegez(args.utolso)
