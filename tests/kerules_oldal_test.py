import math, sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from controllers import baseline_line_follower as b

N = 36


def observe_pontbol(elore_kozep, oldalra):
    """Egyetlen akadalypont (a rover kozeppontjahoz kepest, oldalra<0 = bal)."""
    nyers = [10.0] * N
    ervenyes = [False] * N
    x = elore_kozep - b.LIDAR_ELORE_M
    szog = math.degrees(math.atan2(oldalra, x))
    i = round((szog + 90.0) * (N - 1) / 180.0)
    if 0 <= i < N:
        nyers[i] = math.hypot(x, oldalra)
        ervenyes[i] = True
    return {"lidar_nyers": nyers, "lidar_nyers_ervenyes": ervenyes, "lidar_szektor_min": [10.0] * 6}


class OldalTeszt(unittest.TestCase):
    def test_bal_oldali_akadaly_mellettunk(self):
        # jobbra kerulunk (+1), az akadaly bal oldalt, 0.95 m-re a kozepvonaltol
        self.assertTrue(b.akadaly_oldalt(observe_pontbol(0.3, -0.95), +1, 1.0))

    def test_tavoli_oldalpont_nem_akadaly(self):
        self.assertFalse(b.akadaly_oldalt(observe_pontbol(0.3, -1.6), +1, 1.0))

    def test_masik_oldal_nem_szamit(self):
        self.assertFalse(b.akadaly_oldalt(observe_pontbol(0.3, 0.95), +1, 1.0))
        self.assertTrue(b.akadaly_oldalt(observe_pontbol(0.3, 0.95), -1, 1.0))

    def test_messze_elol_levo_nem_oldalso(self):
        self.assertFalse(b.akadaly_oldalt(observe_pontbol(2.5, -0.5), +1, 1.0))

    def test_regi_1m_kuszob_ala_eso_eset(self):
        # 1.10 m-re oldalt: a regi szektoros dontes (1.0 m) szabadnak latta,
        # pedig a rover oldalatol csak 25 cm.
        self.assertTrue(b.akadaly_oldalt(observe_pontbol(0.3, -1.10), +1, 1.0))

    def test_tartalek_nyers_jel_nelkul(self):
        obs = {"lidar_szektor_min": [0.8, 10, 10, 10, 10, 10]}
        self.assertTrue(b.akadaly_oldalt(obs, +1, 1.0))
        self.assertFalse(b.akadaly_oldalt(obs, -1, 1.0))

    def test_kiteres_a_sopresi_sugaron_kivul_kezdodik(self):
        sarok = math.hypot(b.ROVER_FEL_SZELESSEG_M, b.ROVER_ELEJE_M)
        self.assertGreater(b.ROVER_ELEJE_M + b.AKADALY_KUSZOB_BELEPES_M, sarok + 0.3)


if __name__ == "__main__":
    unittest.main()
