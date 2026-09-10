"""Biztonsagi reteg az agent es a rover backend koze (M12).

Feladatai (a kiiras M12 pontjai szerint):
- csak a szukseges muveleteket engedi at (observe, move, turn, stop,
  reset_position) - get_status/reset_error es minden mas parancs le van tiltva;
- minden parametert a backend ELOTT validal: ervenytelen hivas nem jut el a
  roverhez, hanem rovid, egyertelmu hibauzenettel ter vissza;
- session-limitek: max parancsszam, max idotartam, max osszes megtett tavolsag;
  limit atlepesekor automatikus stop, es a session lezarul;
- backend-rejtes: a valaszbol eltavolitja a privilegizalt szimulator-mezoket
  (position, speed, collision_*), igy az agent nem tudja meg, hogy Unity vagy
  mock all mogotte, es nem is tamaszkodhat "isteni" pozicioadatra.

Az adapter sajat hibai (nem a v1 protokoll hibakodjai) "ADAPTER_" prefixszel
jelennek meg, hogy a naplobol egyertelmu legyen, hol akadt el a hivas.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from adapter.backend import (
    MOVE_SEB_MAX,
    MOVE_SEB_MIN,
    MOVE_TAV_MAX,
    MOVE_TAV_MIN,
    TURN_SEB_MAX,
    TURN_SEB_MIN,
    TURN_SZOG_MAX_ABS,
    TURN_SZOG_MIN_ABS,
    Backend,
)

ENGEDELYEZETT_PARANCSOK = ("observe", "move", "turn", "stop", "reset_position")
ELREJTETT_MEZOK = ("position", "speed", "collision_occurred", "collision_count")


@dataclass(frozen=True)
class SessionKorlatok:
    max_parancs: int = 300
    max_idotartam_s: float = 900.0
    max_ossz_tavolsag_m: float = 60.0
    # egyetlen move maximalis hossza az adapter szintjen (szigorubb a v1 2.0 m-nel):
    max_move_tav_m: float = 1.0


@dataclass
class SessionAllapot:
    kezdet: float = field(default_factory=time.monotonic)
    parancsok: int = 0
    ossz_tavolsag_m: float = 0.0
    lezarva: bool = False
    lezaras_oka: str | None = None
    elutasitott: int = 0


def _adapter_hiba(nev: str, uzenet: str) -> dict[str, Any]:
    return {"status": "rejected", "error": {"code": nev, "message": uzenet}}


def _szam(ertek: Any, nev: str, lo: float, hi: float) -> tuple[float | None, dict[str, Any] | None]:
    if isinstance(ertek, bool) or not isinstance(ertek, (int, float)):
        return None, _adapter_hiba(
            "ADAPTER_INVALID_TYPE", f"{nev} must be a number, got {type(ertek).__name__}"
        )
    if not math.isfinite(ertek):
        return None, _adapter_hiba("ADAPTER_NON_FINITE", f"{nev} must be finite")
    if not lo <= ertek <= hi:
        return None, _adapter_hiba(
            "ADAPTER_OUT_OF_RANGE", f"{nev} must be between {lo} and {hi}, got {ertek}"
        )
    return float(ertek), None


class Orseg:
    def __init__(self, backend: Backend, korlatok: SessionKorlatok | None = None) -> None:
        self._backend = backend
        self.korlatok = korlatok or SessionKorlatok()
        self.session = SessionAllapot()

    # --- publikus muveletek ---------------------------------------------------

    def observe(self) -> dict[str, Any]:
        return self._vegrehajt({"command": "observe"})

    def move(self, distance_m: Any, max_speed: Any = 0.2) -> dict[str, Any]:
        tav, hiba = _szam(
            distance_m, "distance_m", MOVE_TAV_MIN, min(MOVE_TAV_MAX, self.korlatok.max_move_tav_m)
        )
        if hiba:
            return self._elutasit(hiba)
        seb, hiba = _szam(max_speed, "max_speed", MOVE_SEB_MIN, MOVE_SEB_MAX)
        if hiba:
            return self._elutasit(hiba)
        if self.session.ossz_tavolsag_m + tav > self.korlatok.max_ossz_tavolsag_m:
            return self._elutasit(
                _adapter_hiba(
                    "ADAPTER_DISTANCE_BUDGET",
                    f"this move would exceed the session distance budget "
                    f"({self.session.ossz_tavolsag_m:.2f} + {tav:.2f} > "
                    f"{self.korlatok.max_ossz_tavolsag_m} m)",
                )
            )
        valasz = self._vegrehajt({"command": "move", "distance_m": tav, "max_speed": seb})
        if valasz.get("status") == "completed":
            self.session.ossz_tavolsag_m += tav
        return valasz

    def turn(self, angle_deg: Any, max_angular_speed: Any = 30.0) -> dict[str, Any]:
        szog, hiba = _szam(angle_deg, "angle_deg", -TURN_SZOG_MAX_ABS, TURN_SZOG_MAX_ABS)
        if hiba:
            return self._elutasit(hiba)
        if abs(szog) < TURN_SZOG_MIN_ABS:
            return self._elutasit(
                _adapter_hiba(
                    "ADAPTER_OUT_OF_RANGE",
                    f"abs(angle_deg) must be at least {TURN_SZOG_MIN_ABS}, got {szog}",
                )
            )
        seb, hiba = _szam(max_angular_speed, "max_angular_speed", TURN_SEB_MIN, TURN_SEB_MAX)
        if hiba:
            return self._elutasit(hiba)
        return self._vegrehajt({"command": "turn", "angle_deg": szog, "max_angular_speed": seb})

    def stop(self) -> dict[str, Any]:
        # A stop mindig atmegy, lezart sessionben is (biztonsagi muvelet).
        valasz = self._backend.kuld({"command": "stop"})
        self.session.parancsok += 1
        return self._szur(valasz)

    def reset_position(self) -> dict[str, Any]:
        return self._vegrehajt({"command": "reset_position"})

    def session_status(self) -> dict[str, Any]:
        eltelt = time.monotonic() - self.session.kezdet
        return {
            "commands_used": self.session.parancsok,
            "commands_limit": self.korlatok.max_parancs,
            "elapsed_s": round(eltelt, 1),
            "time_limit_s": self.korlatok.max_idotartam_s,
            "distance_used_m": round(self.session.ossz_tavolsag_m, 3),
            "distance_limit_m": self.korlatok.max_ossz_tavolsag_m,
            "max_single_move_m": min(MOVE_TAV_MAX, self.korlatok.max_move_tav_m),
            "rejected_calls": self.session.elutasitott,
            "closed": self.session.lezarva,
            "closed_reason": self.session.lezaras_oka,
        }

    def lezar(self, ok: str) -> None:
        if not self.session.lezarva:
            self.session.lezarva = True
            self.session.lezaras_oka = ok
            try:
                self._backend.kuld({"command": "stop"})
            finally:
                self._backend.close()

    # --- belso ----------------------------------------------------------------

    def _elutasit(self, hiba: dict[str, Any]) -> dict[str, Any]:
        self.session.elutasitott += 1
        return hiba

    def _vegrehajt(self, parancs: dict[str, Any]) -> dict[str, Any]:
        assert parancs["command"] in ENGEDELYEZETT_PARANCSOK
        if self.session.lezarva:
            return self._elutasit(
                _adapter_hiba(
                    "ADAPTER_SESSION_CLOSED", f"session closed: {self.session.lezaras_oka}"
                )
            )
        if self.session.parancsok >= self.korlatok.max_parancs:
            self.lezar("command limit reached")
            return self._elutasit(
                _adapter_hiba("ADAPTER_SESSION_CLOSED", "session closed: command limit reached")
            )
        if time.monotonic() - self.session.kezdet > self.korlatok.max_idotartam_s:
            self.lezar("time limit reached")
            return self._elutasit(
                _adapter_hiba("ADAPTER_SESSION_CLOSED", "session closed: time limit reached")
            )
        self.session.parancsok += 1
        valasz = self._backend.kuld(parancs)
        return self._szur(valasz)

    @staticmethod
    def _szur(valasz: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in valasz.items() if k not in ELREJTETT_MEZOK and k != "request_id"}
