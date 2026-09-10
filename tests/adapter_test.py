"""M12 adapter-tesztek mock backenddel (nem igenyelnek Unity-t)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adapter.backend import MockAkadaly, MockBackend, tavolsag_a_kozepvonaltol  # noqa: E402
from adapter.orseg import ELREJTETT_MEZOK, Orseg, SessionKorlatok  # noqa: E402


class MockBackendTeszt(unittest.TestCase):
    def test_kezdo_pozicio_a_vonalon(self):
        b = MockBackend()
        obs = b.kuld({"command": "observe"})
        self.assertEqual(obs["status"], "completed")
        self.assertTrue(obs["sensor_center"]["white"])
        self.assertEqual(len(obs["lidar_szektor_min"]), 6)

    def test_geometria_fantom_iv_nelkul(self):
        # (0, 2): a javitas elott 0 lett volna, helyesen 4 m
        self.assertAlmostEqual(tavolsag_a_kozepvonaltol(0.0, 2.0), 4.0, places=6)
        self.assertAlmostEqual(tavolsag_a_kozepvonaltol(4.0, 0.0), 0.0, places=6)
        self.assertAlmostEqual(tavolsag_a_kozepvonaltol(0.0, 10.0), 0.0, places=6)

    def test_move_halad_es_v1_hibakodok(self):
        b = MockBackend()
        v = b.kuld({"command": "move", "distance_m": 0.5, "max_speed": 0.2})
        self.assertEqual(v["status"], "completed")
        self.assertAlmostEqual(b.z, 0.5, places=6)
        v = b.kuld({"command": "move", "distance_m": 5.0, "max_speed": 0.2})
        self.assertEqual(v["error"]["code"], 1203)
        v = b.kuld({"command": "move", "distance_m": "x", "max_speed": 0.2})
        self.assertEqual(v["error"]["code"], 1101)
        v = b.kuld({"command": "fly"})
        self.assertEqual(v["error"]["code"], 1200)

    def test_akadaly_utkozes_es_lidar(self):
        b = MockBackend(akadalyok=[MockAkadaly(x=4.0, z=1.0)])
        obs = b.kuld({"command": "observe"})
        self.assertLess(min(obs["lidar_szektor_min"]), 1.0)
        b.kuld({"command": "move", "distance_m": 1.0, "max_speed": 0.2})
        self.assertEqual(b.utkozesek, 1)
        self.assertLess(b.z, 0.7)


class OrsegTeszt(unittest.TestCase):
    def setUp(self):
        self.backend = MockBackend()
        self.orseg = Orseg(self.backend, SessionKorlatok(max_parancs=5, max_ossz_tavolsag_m=1.5))

    def test_ervenytelen_hivas_nem_jut_a_backendhez(self):
        elotte = len(self.backend.parancsnaplo)
        rosszak = [
            ("x", 0.2),
            (5.0, 0.2),
            (0.5, 9.9),
            (float("nan"), 0.2),
            (True, 0.2),
            (-0.1, 0.2),
        ]
        for rossz in rosszak:
            v = self.orseg.move(*rossz)
            self.assertEqual(v["status"], "rejected", rossz)
            self.assertTrue(v["error"]["code"].startswith("ADAPTER_"), rossz)
        self.assertEqual(
            len(self.backend.parancsnaplo), elotte, "a backend nem kaphatott parancsot"
        )
        self.assertEqual(self.orseg.session.elutasitott, 6)

    def test_turn_validacio(self):
        self.assertEqual(self.orseg.turn(0.5)["status"], "rejected")
        self.assertEqual(self.orseg.turn(200)["status"], "rejected")
        self.assertEqual(self.orseg.turn(30, 100)["status"], "rejected")
        self.assertEqual(self.orseg.turn(-30)["status"], "completed")

    def test_backend_rejtes(self):
        obs = self.orseg.observe()
        for mezo in ELREJTETT_MEZOK:
            self.assertNotIn(mezo, obs)
        self.assertNotIn("request_id", obs)
        self.assertIn("sensor_center", obs)
        self.assertIn("lidar_szektor_min", obs)

    def test_parancslimit_automatikus_stop(self):
        for _ in range(5):
            self.assertEqual(self.orseg.observe()["status"], "completed")
        v = self.orseg.observe()
        self.assertEqual(v["error"]["code"], "ADAPTER_SESSION_CLOSED")
        self.assertTrue(self.orseg.session.lezarva)
        self.assertEqual(
            self.backend.parancsnaplo[-1]["command"], "stop", "lezaraskor stop-ot kell kuldeni"
        )
        # lezart sessionben minden mas elutasitva, a stop viszont atmegy
        self.assertEqual(self.orseg.move(0.1)["error"]["code"], "ADAPTER_SESSION_CLOSED")
        self.assertEqual(self.orseg.stop()["status"], "completed")

    def test_tavolsagkeret(self):
        self.assertEqual(self.orseg.move(1.0)["status"], "completed")
        v = self.orseg.move(0.6)
        self.assertEqual(v["error"]["code"], "ADAPTER_DISTANCE_BUDGET")
        self.assertEqual(self.orseg.move(0.5)["status"], "completed")
        self.assertAlmostEqual(self.orseg.session_status()["distance_used_m"], 1.5)

    def test_idolimit(self):
        import time

        o = Orseg(MockBackend(), SessionKorlatok(max_idotartam_s=0.0))
        time.sleep(0.01)
        self.assertEqual(o.observe()["error"]["code"], "ADAPTER_SESSION_CLOSED")
        self.assertEqual(o.session_status()["closed_reason"], "time limit reached")

    def test_session_status_mezok(self):
        s = self.orseg.session_status()
        for k in (
            "commands_used",
            "commands_limit",
            "distance_used_m",
            "distance_limit_m",
            "closed",
        ):
            self.assertIn(k, s)


if __name__ == "__main__":
    unittest.main()
