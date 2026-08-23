#!/usr/bin/env python3
"""Unit tesztek a baseline vonalkövető állapotgépéhez - M10.

Ezt a fájlt Claude írta (lásd AI_USAGE.md), Dalma review-ja mellett.
Ellentétben a `protocol_fuzz_test.py`-jal, ez a teszt NEM igényel
futó Unity szervert: egy StubKliens-t injektál a
`gateway/client.py`-hoz hasonló interfésszel, ami előre megadott
`observe` válaszokat ad vissza. Ez azt teszteli, hogy a
`controllers/baseline_line_follower.py` állapotgépe (VONALON /
AKADÁLY / VISSZATALALAS / KERESÉS) a specifikációnak megfelelően
vált állapotot - nem azt, hogy a Unity-szimuláció fizikailag helyesen
viselkedik (azt a Play Mode-os manuális/videós tesztek és a
jövőbeli, Unityt igénylő integrációs tesztek fedik le).

Futtatás:
    python3 tests/baseline_line_follower_test.py
    python3 -m pytest -v tests/baseline_line_follower_test.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

GYOKER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GYOKER / "controllers"))

from baseline_line_follower import (  # noqa: E402
    Allapot,
    FutasStatisztika,
    VISSZATALALAS_MAX_LEPES,
    ZSAKUTCA_AKADALY_MAX_LEPES,
    egy_lepes_akadaly,
    egy_lepes_kereses,
    egy_lepes_visszatalalas,
    egy_lepes_vonalon,
)


class StubGatewayKliens:
    """Előre megadott observe-válaszokat visszaadó, hálózat nélküli stub.

    A move/turn parancsokra egyszerű "completed" választ ad, ezeket nem
    kell előre megadni - csak az observe válaszok sorrendje számít.
    """

    def __init__(self, observe_valaszok: list[dict[str, Any]]) -> None:
        self._observe_valaszok = list(observe_valaszok)
        self.kuldott_parancsok: list[dict[str, Any]] = []

    def kuld(self, parancs: dict[str, Any]) -> dict[str, Any]:
        self.kuldott_parancsok.append(parancs)
        if parancs["command"] == "observe":
            if not self._observe_valaszok:
                raise AssertionError("Nem volt tobb elokeszitett observe valasz.")
            return self._observe_valaszok.pop(0)
        return {"status": "completed"}


def observe_valasz(
    white: bool = False,
    akadaly_tavolsag_m: float = 5.0,
    intensity_bal: float = 0.0,
    intensity_jobb: float = 0.0,
) -> dict[str, Any]:
    return {
        "sensor_left": {"white": white, "intensity": intensity_bal},
        "sensor_center": {"white": white, "intensity": 0.0},
        "sensor_right": {"white": white, "intensity": intensity_jobb},
        "lidar_szektor_min": [akadaly_tavolsag_m] * 6,
        "position": {"x": 0.0, "y": 0.0, "z": 0.0},
        "collision_occurred": False,
        "collision_count": 0,
    }


class AllapotgepAtmenetekTest(unittest.TestCase):
    def test_vonalon_akadaly_eszleleskor_atvalt_akadalyra(self) -> None:
        stat = FutasStatisztika()
        kliens = StubGatewayKliens([observe_valasz(white=True, akadaly_tavolsag_m=0.3)])
        uj_allapot = egy_lepes_vonalon(kliens, stat, [1], None, 0)
        self.assertIs(uj_allapot, Allapot.AKADALY)
        self.assertEqual(stat.akadaly_kerulesek_szama, 1)

    def test_vonalon_vonalvesztesnel_atvalt_keresesre(self) -> None:
        stat = FutasStatisztika()
        kliens = StubGatewayKliens([observe_valasz(white=False, akadaly_tavolsag_m=5.0)])
        uj_allapot = egy_lepes_vonalon(kliens, stat, [1], None, 0)
        self.assertIs(uj_allapot, Allapot.KERESES)
        self.assertEqual(stat.vonalvesztesek_szama, 1)

    def test_akadaly_kozeli_akadalynal_marad_akadalyban_es_iranyt_jegyez(self) -> None:
        stat = FutasStatisztika()
        irany = [0]
        kliens = StubGatewayKliens([observe_valasz(akadaly_tavolsag_m=0.3)])
        uj_allapot = egy_lepes_akadaly(kliens, stat, irany, [0], None, 0)
        self.assertIs(uj_allapot, Allapot.AKADALY)
        self.assertIn(irany[0], (1, -1))

    def test_akadaly_elhagyasakor_visszatalalasra_valt_nem_kozvetlenul_vonalonra(self) -> None:
        stat = FutasStatisztika()
        kliens = StubGatewayKliens([observe_valasz(akadaly_tavolsag_m=5.0)])
        uj_allapot = egy_lepes_akadaly(kliens, stat, [1], [0], None, 0)
        self.assertIs(uj_allapot, Allapot.VISSZATALALAS)

    def test_akadaly_zsakutca_eszleles_eskalal_keresesre(self) -> None:
        stat = FutasStatisztika()
        # ZSAKUTCA_AKADALY_MAX_LEPES-szer egymas utan "meg mindig akadaly
        # elottunk" valaszt adunk - ez szimulalja, hogy a rover nem tud
        # kikerulni (pl. ket akadaly koze szorult).
        valaszok = [
            observe_valasz(akadaly_tavolsag_m=0.3) for _ in range(ZSAKUTCA_AKADALY_MAX_LEPES)
        ]
        kliens = StubGatewayKliens(valaszok)
        irany = [1]
        lepesek = [0]
        uj_allapot = Allapot.AKADALY
        for _ in range(ZSAKUTCA_AKADALY_MAX_LEPES):
            uj_allapot = egy_lepes_akadaly(kliens, stat, irany, lepesek, None, 0)
        self.assertIs(uj_allapot, Allapot.KERESES)
        self.assertEqual(stat.zsakutcak_szama, 1)
        self.assertEqual(lepesek[0], 0)

    def test_visszatalalas_azonnal_vonalon_ha_mar_feher_a_szenzor(self) -> None:
        stat = FutasStatisztika()
        kliens = StubGatewayKliens([observe_valasz(white=True)])
        uj_allapot = egy_lepes_visszatalalas(kliens, stat, [1], [0], None, 0)
        self.assertIs(uj_allapot, Allapot.VONALON)

    def test_visszatalalas_forgas_es_mozgas_utan_megtalalja_a_vonalat(self) -> None:
        stat = FutasStatisztika()
        kliens = StubGatewayKliens(
            [observe_valasz(white=False), observe_valasz(white=True)]
        )
        uj_allapot = egy_lepes_visszatalalas(kliens, stat, [1], [0], None, 0)
        self.assertIs(uj_allapot, Allapot.VONALON)

    def test_visszatalalas_max_lepes_utan_eszkalal_keresesre(self) -> None:
        stat = FutasStatisztika()
        visszatalalas_lepesek = [0]
        allapot = Allapot.VISSZATALALAS
        lepesszam = 0
        # +2 biztonsagi ratartas, hogy biztosan tuljussunk a korlaton.
        while lepesszam < VISSZATALALAS_MAX_LEPES + 2:
            kliens = StubGatewayKliens(
                [observe_valasz(white=False), observe_valasz(white=False)]
            )
            allapot = egy_lepes_visszatalalas(
                kliens, stat, [1], visszatalalas_lepesek, None, lepesszam
            )
            lepesszam += 1
            if allapot is not Allapot.VISSZATALALAS:
                break
        self.assertIs(allapot, Allapot.KERESES)
        self.assertLessEqual(lepesszam, VISSZATALALAS_MAX_LEPES + 1)

    def test_kereses_vonal_megtalalasakor_visszavalt_vonalonra(self) -> None:
        stat = FutasStatisztika()
        kliens = StubGatewayKliens([observe_valasz(white=True)])
        uj_allapot = egy_lepes_kereses(kliens, stat, [1], [0], None, 0)
        self.assertIs(uj_allapot, Allapot.VONALON)

    def test_kereses_max_lepes_utan_palyaelhagyast_jelez(self) -> None:
        stat = FutasStatisztika()
        kereses_lepesek = [0]
        from baseline_line_follower import KERESES_MAX_LEPES

        for lepes in range(KERESES_MAX_LEPES):
            kliens = StubGatewayKliens([observe_valasz(white=False)])
            egy_lepes_kereses(kliens, stat, [1], kereses_lepesek, None, lepes)
        self.assertTrue(stat.palyaelhagyas)


if __name__ == "__main__":
    unittest.main()