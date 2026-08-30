"""M11: unit tesztek a common.kiserlet_naplo modulhoz."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_PROJEKT_GYOKER = str(Path(__file__).resolve().parent.parent)
if _PROJEKT_GYOKER not in sys.path:
    sys.path.insert(0, _PROJEKT_GYOKER)

from common.kiserlet_naplo import KiserletMetaadat, KiserletNaplozo


class KiserletNaplozoTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.naplo_fajl = Path(self._tmp_dir.name) / "teszt_naplo.jsonl"

    def tearDown(self) -> None:
        self._tmp_dir.cleanup()

    def test_alap_bejegyzes_mezoi_helyesek(self) -> None:
        metaadat = KiserletMetaadat(controller="teszt_controller", backend="teszt_backend", seed=42)
        with KiserletNaplozo(self.naplo_fajl, "run-1", metaadat) as naplo:
            naplo.rogzit(
                lepes_szam=0,
                szenzorok={"sensor_left": {"white": True}},
                parancsok=[{"command": "move", "distance_m": 0.1}],
                allapot_elotte="VONALON",
                allapot_utana="VONALON",
                privilegizalt_diagnosztika={"position": {"x": 1.0, "y": 0.0, "z": 2.0}},
            )

        sorok = self.naplo_fajl.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(sorok), 1)
        bejegyzes = json.loads(sorok[0])

        self.assertEqual(bejegyzes["run_id"], "run-1")
        self.assertEqual(bejegyzes["controller"], "teszt_controller")
        self.assertEqual(bejegyzes["backend"], "teszt_backend")
        self.assertEqual(bejegyzes["seed"], 42)
        self.assertEqual(bejegyzes["lepes_szam"], 0)
        self.assertEqual(bejegyzes["allapot_elotte"], "VONALON")
        self.assertEqual(bejegyzes["allapot_utana"], "VONALON")
        self.assertEqual(bejegyzes["szenzorok"], {"sensor_left": {"white": True}})
        self.assertEqual(bejegyzes["parancsok"], [{"command": "move", "distance_m": 0.1}])
        self.assertEqual(bejegyzes["privilegizalt_diagnosztika"]["position"]["x"], 1.0)

    def test_tobb_lepes_hozzafuzodik_nem_felulirodik(self) -> None:
        metaadat = KiserletMetaadat(controller="c", backend="b", seed=None)
        with KiserletNaplozo(self.naplo_fajl, "run-2", metaadat) as naplo:
            naplo.rogzit(0, {}, [])
            naplo.rogzit(1, {}, [])
            naplo.rogzit(2, {}, [])

        sorok = self.naplo_fajl.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(sorok), 3)
        lepesszamok = [json.loads(s)["lepes_szam"] for s in sorok]
        self.assertEqual(lepesszamok, [0, 1, 2])

    def test_seed_nelkul_is_mukodik(self) -> None:
        metaadat = KiserletMetaadat(controller="c", backend="b")
        with KiserletNaplozo(self.naplo_fajl, "run-3", metaadat) as naplo:
            naplo.rogzit(0, {}, [])

        bejegyzes = json.loads(self.naplo_fajl.read_text(encoding="utf-8").strip())
        self.assertIsNone(bejegyzes["seed"])

    def test_privilegizalt_diagnosztika_alapertelmezetten_none(self) -> None:
        metaadat = KiserletMetaadat(controller="c", backend="b")
        with KiserletNaplozo(self.naplo_fajl, "run-4", metaadat) as naplo:
            naplo.rogzit(0, {}, [])

        bejegyzes = json.loads(self.naplo_fajl.read_text(encoding="utf-8").strip())
        self.assertIsNone(bejegyzes["privilegizalt_diagnosztika"])

    def test_ket_kulon_naplozo_ugyanabba_a_fajlba_ir(self) -> None:
        """Ket 'futas' (pl. ket egymas utani kiserlet) ugyanabba a
        kozos naplofajlba irhat, run_id alapjan megkulonboztethetoen -
        ez a kivant viselkedes az M11-es egyseges naplo szamara."""
        metaadat = KiserletMetaadat(controller="c", backend="b")
        with KiserletNaplozo(self.naplo_fajl, "run-A", metaadat) as naplo:
            naplo.rogzit(0, {}, [])
        with KiserletNaplozo(self.naplo_fajl, "run-B", metaadat) as naplo:
            naplo.rogzit(0, {}, [])

        sorok = self.naplo_fajl.read_text(encoding="utf-8").strip().splitlines()
        run_idk = {json.loads(s)["run_id"] for s in sorok}
        self.assertEqual(run_idk, {"run-A", "run-B"})


if __name__ == "__main__":
    unittest.main()