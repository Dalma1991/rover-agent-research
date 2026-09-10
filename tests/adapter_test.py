"""M12 adapter-tesztek mock backenddel (nem igenyelnek Unity-t)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adapter.backend import MockAkadaly, MockBackend, tavolsag_a_kozepvonaltol  # noqa: E402
from adapter.orseg import (  # noqa: E402
    ELREJTETT_MEZOK,
    UTKOZES_MEZO,
    Orseg,
    SessionKorlatok,
)


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


class HibasBackend:
    """Backend, ami a megadott hivasszam utan kivetelt dob (halozati hiba)."""

    def __init__(self, hibatol: int = 0, kivetel=None) -> None:
        self.hivasok = 0
        self.hibatol = hibatol
        self.kivetel = kivetel or ConnectionError("A kapcsolat varatlanul megszakadt.")
        self.lezarva = False

    def kuld(self, parancs):
        self.hivasok += 1
        if self.hivasok > self.hibatol:
            raise self.kivetel
        return {"status": "completed", "state": "IDLE"}

    def close(self) -> None:
        self.lezarva = True


class BiztonsagiJavitasokTeszt(unittest.TestCase):
    """A M12 security review talalatainak regresszios tesztjei."""

    def test_1_backend_kivetel_nem_szivarog_ki(self):
        backend = HibasBackend()
        orseg = Orseg(backend)
        valasz = orseg.observe()
        self.assertEqual(valasz["error"]["code"], "ADAPTER_BACKEND_ERROR")
        self.assertNotIn("ConnectionError", json.dumps(valasz))
        self.assertNotIn("megszakadt", json.dumps(valasz))
        self.assertTrue(orseg.session.lezarva, "backend-hiba eseten a session lezarul")
        self.assertTrue(backend.lezarva, "a backendet le kell zarni")

    def test_1b_nem_dict_valasz_is_kezelve(self):
        class RosszValaszBackend(HibasBackend):
            def kuld(self, parancs):
                return "nem dict"

        orseg = Orseg(RosszValaszBackend())
        self.assertEqual(orseg.observe()["error"]["code"], "ADAPTER_BACKEND_ERROR")

    def test_2_utkozesjelzes_lathato_de_a_szamlalo_nem(self):
        backend = MockBackend(akadalyok=[MockAkadaly(x=4.0, z=0.5)])
        orseg = Orseg(backend)
        elso = orseg.observe()
        self.assertFalse(elso[UTKOZES_MEZO], "meg nem volt utkozes")
        orseg.move(0.5)
        masodik = orseg.observe()
        self.assertTrue(masodik[UTKOZES_MEZO], "az utkozest jeleznie kell")
        for mezo in ELREJTETT_MEZOK:
            self.assertNotIn(mezo, masodik, f"{mezo} nem szivaroghat ki")
        harmadik = orseg.observe()
        self.assertFalse(harmadik[UTKOZES_MEZO], "a jelzes az observe utan nullazodik")

    def test_3_stop_lezart_sessionben_nem_hasznalja_a_backendet(self):
        backend = MockBackend()
        orseg = Orseg(backend, SessionKorlatok(max_parancs=1))
        orseg.observe()
        orseg.observe()
        self.assertTrue(orseg.session.lezarva)
        hivasok = len(backend.parancsnaplo)
        valasz = orseg.stop()
        self.assertEqual(valasz["status"], "completed")
        self.assertEqual(len(backend.parancsnaplo), hivasok, "lezart backendre nem kuldunk")

    def test_4_elutasitott_hivas_is_fogyasztja_a_keretet(self):
        orseg = Orseg(MockBackend(), SessionKorlatok(max_parancs=3))
        for _ in range(3):
            self.assertEqual(orseg.move(99.0)["status"], "rejected")
        self.assertEqual(orseg.session.parancsok, 3)
        self.assertEqual(orseg.observe()["error"]["code"], "ADAPTER_SESSION_CLOSED")

    def test_7_tiltott_parancs_raise_nem_assert(self):
        orseg = Orseg(MockBackend())
        with self.assertRaises(ValueError):
            orseg._vegrehajt({"command": "reset_error"})

    def test_lezaras_hibas_backenddel_sem_dob(self):
        class MindigHibas(HibasBackend):
            def close(self) -> None:
                raise OSError("close hiba")

        orseg = Orseg(MindigHibas())
        orseg.lezar("teszt")
        self.assertTrue(orseg.session.lezarva)


if __name__ == "__main__":
    unittest.main()
