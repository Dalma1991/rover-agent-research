"""M11: egységes kísérlet-naplózó modul."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class KiserletMetaadat:
    controller: str
    backend: str
    seed: int | None = None


class KiserletNaplozo:
    def __init__(
        self,
        fajl: Path,
        run_id: str,
        metaadat: KiserletMetaadat,
    ) -> None:
        self.fajl = fajl
        self.run_id = run_id
        self.metaadat = metaadat
        self.fajl.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.fajl.open("a", encoding="utf-8")

    def rogzit(
        self,
        lepes_szam: int,
        szenzorok: dict[str, Any],
        parancsok: list[dict[str, Any]],
        allapot_elotte: str | None = None,
        allapot_utana: str | None = None,
        privilegizalt_diagnosztika: dict[str, Any] | None = None,
    ) -> None:
        bejegyzes = {
            "run_id": self.run_id,
            "controller": self.metaadat.controller,
            "backend": self.metaadat.backend,
            "seed": self.metaadat.seed,
            "idobelyeg": datetime.now(timezone.utc).isoformat(),
            "lepes_szam": lepes_szam,
            "allapot_elotte": allapot_elotte,
            "allapot_utana": allapot_utana,
            "szenzorok": szenzorok,
            "parancsok": parancsok,
            "privilegizalt_diagnosztika": privilegizalt_diagnosztika,
        }
        json.dump(bejegyzes, self._fh, ensure_ascii=False, separators=(",", ":"))
        self._fh.write("\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()

    def __enter__(self) -> "KiserletNaplozo":
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()