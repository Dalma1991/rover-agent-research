#!/usr/bin/env python3
"""Validacios szcenario: a palya meretei is a nevbol kepzett seedbol jonnek.

A nev, a tipus es a tartomanyok a generalas ELOTT rogzitettek (docs/m10-plan.md,
validacios terv), igy a palyat nem mi valasztjuk ki. Az akadalyok vegig lathatok.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

GYOKER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GYOKER / "scripts"))

from generate_example_scenarios import between, obstacle  # noqa: E402
from generate_scenario_seed import scenario_seed  # noqa: E402

NEV = "stadium-validation-20261008"
TIPUS = "dev"
TARTOMANYOK = {
    "straight_length_m": (10.0, 16.0),
    "turn_radius_m": (3.5, 5.0),
    "line_width_m": (0.14, 0.22),
}
AKADALYOK_SZAMA = 2
MINDIG_LATHATO = {"appear_at_s": 0.0, "visible_for_s": 100000.0, "disappear_at_s": 100000.0}


def main() -> int:
    seed = scenario_seed(TIPUS, NEV)
    palya = {k: between(seed, "track:" + k, lo, hi) for k, (lo, hi) in TARTOMANYOK.items()}
    palya["background_color_rgb"] = {"r": 30, "g": 33, "b": 38}
    akadalyok = [
        obstacle(seed, "validation", i, palya["straight_length_m"], palya["turn_radius_m"])
        for i in range(AKADALYOK_SZAMA)
    ]
    for akadaly in akadalyok:
        akadaly["schedule"] = dict(MINDIG_LATHATO)
    dokumentum = {
        "schema_version": "1.0",
        "metadata": {"name": NEV + "-always-visible", "type": TIPUS, "seed": seed},
        "track": palya,
        "obstacles": akadalyok,
    }
    cel = GYOKER / "experiments" / "scenarios" / (NEV + "-always-visible.json")
    if cel.exists():
        print(f"Mar letezik: {cel}", file=sys.stderr)
        return 1
    cel.write_text(json.dumps(dokumentum, indent=2) + "\n", encoding="utf-8")
    print(f"{cel.name}: seed={seed}, {palya}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
