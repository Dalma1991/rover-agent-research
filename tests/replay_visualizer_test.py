"""M11: unit tesztek a replay_visualizer.py utkozes-detektalasahoz."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_PROJEKT_GYOKER = str(Path(__file__).resolve().parent.parent)
if _PROJEKT_GYOKER not in sys.path:
    sys.path.insert(0, _PROJEKT_GYOKER)

from controllers.replay_visualizer import legutolso_run_id


def _pozicio(x: float, z: float) -> dict:
    return {"x": x, "y": 0.25, "z": z}


def utkozesek_kigyujtese(sorok: list[dict]) -> tuple[list[float], list[float]]:
    """A replay_visualizer.py rajzol()-jaban levo utkozes-gyujto logika
    kulon fuggvenyben, hogy onmagaban tesztelheto legyen."""
    utkozes_x, utkozes_z = [], []
    elozo_szamlalo = 0
    for sor in sorok:
        diag = sor.get("privilegizalt_diagnosztika") or {}
        szamlalo = diag.get("collision_count") or 0
        if szamlalo > elozo_szamlalo and diag.get("position"):
            utkozes_x.append(diag["position"]["x"])
            utkozes_z.append(diag["position"]["z"])
        elozo_szamlalo = szamlalo
    return utkozes_x, utkozes_z


class UtkozesDetektalasTest(unittest.TestCase):
    def test_ragados_collision_occurred_nem_jelol_minden_lepest(self) -> None:
        """Ez a teszt pontosan azt a hibat rogziti regresszios tesztkent,
        amit a mai session soran a valodi replay-kepen eszrevettunk: a
        collision_occurred 'ragados' mezo, de a collision_count valtozasa
        csak a tenyleges uj utkozeseket jeloli."""
        sorok = [
            {
                "privilegizalt_diagnosztika": {
                    "position": _pozicio(0, 0),
                    "collision_occurred": False,
                    "collision_count": 0,
                }
            },
            {
                "privilegizalt_diagnosztika": {
                    "position": _pozicio(1, 0),
                    "collision_occurred": True,
                    "collision_count": 1,
                }
            },
            # a collision_occurred "ragadva" marad True-n, de nincs UJ utkozes:
            {
                "privilegizalt_diagnosztika": {
                    "position": _pozicio(2, 0),
                    "collision_occurred": True,
                    "collision_count": 1,
                }
            },
            {
                "privilegizalt_diagnosztika": {
                    "position": _pozicio(3, 0),
                    "collision_occurred": True,
                    "collision_count": 1,
                }
            },
        ]
        utkozes_x, utkozes_z = utkozesek_kigyujtese(sorok)
        self.assertEqual(utkozes_x, [1])
        self.assertEqual(utkozes_z, [0])

    def test_ket_kulon_utkozes_mindkettot_jeloli(self) -> None:
        sorok = [
            {"privilegizalt_diagnosztika": {"position": _pozicio(0, 0), "collision_count": 0}},
            {"privilegizalt_diagnosztika": {"position": _pozicio(1, 0), "collision_count": 1}},
            {"privilegizalt_diagnosztika": {"position": _pozicio(2, 0), "collision_count": 1}},
            {"privilegizalt_diagnosztika": {"position": _pozicio(3, 0), "collision_count": 2}},
        ]
        utkozes_x, _ = utkozesek_kigyujtese(sorok)
        self.assertEqual(utkozes_x, [1, 3])

    def test_hianyzo_diagnosztika_nem_okoz_hibat(self) -> None:
        sorok = [
            {"privilegizalt_diagnosztika": None},
            {"privilegizalt_diagnosztika": {"position": _pozicio(1, 0), "collision_count": 1}},
        ]
        utkozes_x, _ = utkozesek_kigyujtese(sorok)
        self.assertEqual(utkozes_x, [1])

    def test_legutolso_run_id_az_utolso_sort_adja_vissza(self) -> None:
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            naplo_fajl = Path(tmp) / "naplo.jsonl"
            with naplo_fajl.open("w", encoding="utf-8") as f:
                f.write(json.dumps({"run_id": "elso"}) + "\n")
                f.write(json.dumps({"run_id": "masodik"}) + "\n")

            self.assertEqual(legutolso_run_id(naplo_fajl), "masodik")


if __name__ == "__main__":
    unittest.main()
