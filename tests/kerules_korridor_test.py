"""A kerules korridor-alapu akadalyfelismeresenek tesztjei (Unity nelkul)."""

import sys
import unittest
from pathlib import Path

GYOKER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GYOKER))
sys.path.insert(0, str(GYOKER / "controllers"))

from baseline_line_follower import akadaly_elol  # noqa: E402


def _observe(talalatok, n=36):
    nyers, maszk = [10.0] * n, [False] * n
    for i, r in talalatok.items():
        nyers[i], maszk[i] = r, True
    return {"lidar_nyers": nyers, "lidar_nyers_ervenyes": maszk, "lidar_szektor_min": [10.0] * 6}


def _index(szog_fok, n=36):
    return round((szog_fok + 90.0) / (180.0 / (n - 1)))


class KorridorTeszt(unittest.TestCase):
    def test_oldalt_a_kerek_vonalaban(self):
        # 50 fokra, 0.9 m-re: oldalt ~0.68 m, a kerek vonalaban. A regi,
        # csak a +-30 fokos szektorokat nezo logika ezt nem latta.
        self.assertTrue(akadaly_elol(_observe({_index(50): 0.9}), 0.5))

    def test_a_rover_savjan_kivul(self):
        self.assertFalse(akadaly_elol(_observe({_index(80): 1.5}), 0.5))

    def test_messze_elotte(self):
        self.assertFalse(akadaly_elol(_observe({_index(0): 3.0}), 0.5))

    def test_kozvetlenul_elotte(self):
        self.assertTrue(akadaly_elol(_observe({_index(0): 0.6}), 0.5))

    def test_nem_talalo_sugar_nem_akadaly(self):
        o = _observe({})
        o["lidar_nyers"][_index(0)] = 0.3
        self.assertFalse(akadaly_elol(o, 0.5))


if __name__ == "__main__":
    unittest.main()
