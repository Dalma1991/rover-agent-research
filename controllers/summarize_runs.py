#!/usr/bin/env python3
"""Osszegzo statisztika az M09 baseline kontroller futasi naploibol."""

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

    lepesek = [f["lepesek_szama"] for f in futasok]
    parancsok = [f["parancsok_szama"] for f in futasok]
    vonalveszesek = [f["vonalvesztesek_szama"] for f in futasok]
    akadalykerulesek = [f["akadaly_kerulesek_szama"] for f in futasok]
    palyaelhagyasok = sum(1 for f in futasok if f["palyaelhagyas"])

    print(f"Osszegzes ({len(futasok)} futas):")
    print(f"  Parancsok szama:      atlag={statistics.mean(parancsok):.1f}, "
          f"szoras={statistics.stdev(parancsok):.1f}, "
          f"min={min(parancsok)}, max={max(parancsok)}")
    print(f"  Vonalvesztesek szama: atlag={statistics.mean(vonalveszesek):.1f}, "
          f"szoras={statistics.stdev(vonalveszesek):.1f}, "
          f"min={min(vonalveszesek)}, max={max(vonalveszesek)}")
    print(f"  Akadalykerulesek:     atlag={statistics.mean(akadalykerulesek):.1f}, "
          f"szoras={statistics.stdev(akadalykerulesek):.1f}, "
          f"min={min(akadalykerulesek)}, max={max(akadalykerulesek)}")
    print(f"  Palyaelhagyasok:      {palyaelhagyasok}/{len(futasok)} futasban")


if __name__ == "__main__":
    osszegez()
