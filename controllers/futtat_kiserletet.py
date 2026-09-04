#!/usr/bin/env python3
"""M11: egyparancsos kiserletinditas es eredmeny-osszesites.

Lefuttat N darab baseline_line_follower.py futast egymas utan, majd
a vegen automatikusan lefuttatja a summarize_runs.py-t az osszesitett
eredmenyekkel. Igy nem kell kulon-kulon inditani a mereset es az
osszesitest.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="M11 egyparancsos kiserletinditas")
    parser.add_argument(
        "--futasok-szama",
        type=int,
        default=30,
        help="Hany egymas utani futast inditson el (alapertelmezett: 30).",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--max-lepes", type=int, default=500)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    projekt_gyoker = Path(__file__).resolve().parent.parent
    baseline_szkript = projekt_gyoker / "controllers" / "baseline_line_follower.py"
    summarize_szkript = projekt_gyoker / "controllers" / "summarize_runs.py"

    print(f"=== {args.futasok_szama} futas inditasa ===")
    for i in range(1, args.futasok_szama + 1):
        print(f"--- Futas {i}/{args.futasok_szama} ---")
        parancs = [
            sys.executable,
            str(baseline_szkript),
            "--host",
            args.host,
            "--port",
            str(args.port),
            "--max-lepes",
            str(args.max_lepes),
        ]
        if args.seed is not None:
            parancs += ["--seed", str(args.seed)]

        eredmeny = subprocess.run(parancs)
        if eredmeny.returncode != 0:
            print(f"Hiba tortent a(z) {i}. futasnal, leallitas.", file=sys.stderr)
            return eredmeny.returncode

    print("\n=== Osszesites futtatasa ===")
    osszesito_eredmeny = subprocess.run(
        [sys.executable, str(summarize_szkript), "--utolso", str(args.futasok_szama)]
    )
    return osszesito_eredmeny.returncode


if __name__ == "__main__":
    raise SystemExit(main())
