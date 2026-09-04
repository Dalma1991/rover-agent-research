#!/usr/bin/env python3
"""Reprodukálhatósági teszt: azonos seed = azonos akadálysorozat.

Ezt a fájlt Dalma írta kézzel (nem a Codex), mert a hónapos AI-kvóta
elfogyott az M06 mérföldkő munkája közben. A seed-generáló és a
szcenárió-generáló logika a Codex-szel készült (lásd AI_USAGE.md,
scripts/generate_scenario_seed.py, scripts/generate_example_scenarios.py).

Ez a teszt bizonyítja az M06 elfogadási feltételét:
"Azonos seed és konfiguráció azonos akadályszekvenciát ad."

Futtatás:
    python3 tests/scenario_seed_test.py
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

GYOKER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GYOKER / "scripts"))

from generate_scenario_seed import scenario_seed  # noqa: E402
from generate_example_scenarios import obstacle, SCENARIOS  # noqa: E402


class SzcenarioSeedReprodukalhatosagTest(unittest.TestCase):
    """A seed-képzés és az akadálygenerálás determinisztikus."""

    def test_seed_kepzes_determinisztikus(self):
        """Ugyanaz a (típus, név) pár mindig ugyanazt a seedet adja."""
        for tipus, nev, *_ in SCENARIOS:
            elso = scenario_seed(tipus, nev)
            masodik = scenario_seed(tipus, nev)
            self.assertEqual(
                elso,
                masodik,
                f"A '{tipus}:{nev}' seed nem stabil ismételt hívások között.",
            )

    def test_kulonbozo_nev_kulonbozo_seedet_ad(self):
        """Különböző szcenárió-nevek (jó eséllyel) különböző seedet adnak."""
        seedek = [scenario_seed(tipus, nev) for tipus, nev, *_ in SCENARIOS]
        self.assertEqual(
            len(seedek),
            len(set(seedek)),
            "Két különböző szcenárió ugyanazt a seedet kapta - ez ütközés, "
            "vizsgáld meg a seed-képzés logikáját.",
        )

    def test_akadaly_generalas_determinisztikus(self):
        """Ugyanazokkal a paraméterekkel kétszer generált akadály egyezik."""
        for tipus, nev, hossz, sugar, _szelesseg, _szin, darab in SCENARIOS:
            seed = scenario_seed(tipus, nev)
            for index in range(darab):
                elso = obstacle(seed, tipus, index, hossz, sugar)
                masodik = obstacle(seed, tipus, index, hossz, sugar)
                self.assertEqual(
                    elso,
                    masodik,
                    f"A(z) '{tipus}' szcenárió {index}. akadálya nem "
                    f"reprodukálható ugyanazzal a seeddel.",
                )

    def test_generalt_dokumentum_egyezik_a_bejegyzett_fajllal(self):
        """A repóban tárolt JSON pontosan a jelenlegi generátor kimenete.

        Ez azt is ellenőrzi, hogy a generátor kódja és a bejegyzett
        példafájlok nem csúsztak el egymástól.
        """
        szcenariok_mappa = GYOKER / "experiments" / "scenarios"

        for tipus, nev, hossz, sugar, szelesseg, szin, darab in SCENARIOS:
            fajl_utvonal = szcenariok_mappa / f"{nev}.json"
            if not fajl_utvonal.exists():
                self.skipTest(f"{fajl_utvonal} még nem létezik.")

            with open(fajl_utvonal, "r", encoding="utf-8") as f:
                bejegyzett = json.load(f)

            seed = scenario_seed(tipus, nev)
            ujragenaralt = {
                "schema_version": "1.0",
                "metadata": {"name": nev, "type": tipus, "seed": seed},
                "track": {
                    "straight_length_m": hossz,
                    "turn_radius_m": sugar,
                    "line_width_m": szelesseg,
                    "background_color_rgb": dict(zip(("r", "g", "b"), szin)),
                },
                "obstacles": [obstacle(seed, tipus, index, hossz, sugar) for index in range(darab)],
            }

            self.assertEqual(
                bejegyzett,
                ujragenaralt,
                f"A(z) {fajl_utvonal.name} fájl eltér a jelenlegi generátor "
                f"kimenetétől - futtasd újra: "
                f"python3 scripts/generate_example_scenarios.py",
            )


if __name__ == "__main__":
    unittest.main()
