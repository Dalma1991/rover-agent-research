#!/usr/bin/env python3
"""Interaktív TCP kliens a Unity RoverGatewayServer komponenshez."""

from __future__ import annotations

import argparse
import json
import math
import shlex
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO
from uuid import uuid4


ALAPERTELMEZETT_HOST = "127.0.0.1"
ALAPERTELMEZETT_PORT = 8765
NAPLO_FAJL = Path(__file__).resolve().parent / "logs" / "session.jsonl"


class JsonlNaplo:
    def __init__(self, fajlnev: Path) -> None:
        self.fajlnev = fajlnev
        self.fajl: TextIO | None = None

    def __enter__(self) -> "JsonlNaplo":
        try:
            self.fajlnev.parent.mkdir(parents=True, exist_ok=True)
            self.fajl = self.fajlnev.open("a", encoding="utf-8", buffering=1)
        except OSError as hiba:
            print(f"Figyelmeztetés: a napló nem nyitható meg: {hiba}", file=sys.stderr)
        return self

    def __exit__(self, *_: object) -> None:
        if self.fajl is not None:
            self.fajl.close()

    def rogzit(self, irany: str, uzenet: Any) -> None:
        if self.fajl is None:
            return

        bejegyzes = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "direction": irany,
            "message": uzenet,
        }

        try:
            json.dump(bejegyzes, self.fajl, ensure_ascii=False, separators=(",", ":"))
            self.fajl.write("\n")
        except (OSError, TypeError, ValueError) as hiba:
            print(f"Figyelmeztetés: a napló nem írható: {hiba}", file=sys.stderr)
            self.fajl = None


def parancs_feldolgozasa(sor: str) -> dict[str, Any] | None:
    try:
        reszek = shlex.split(sor)
    except ValueError as hiba:
        raise ValueError(f"Hibás parancs: {hiba}") from hiba

    if not reszek:
        return None

    parancs = reszek[0].lower()
    request_id = str(uuid4())

    if parancs in {"observe", "stop"}:
        if len(reszek) != 1:
            raise ValueError(f"Használat: {parancs}")
        return {"request_id": request_id, "command": parancs}

    if parancs == "move":
        if len(reszek) != 3:
            raise ValueError("Használat: move <distance_m> <max_speed>")

        try:
            tavolsag = float(reszek[1])
            maximalis_sebesseg = float(reszek[2])
        except ValueError as hiba:
            raise ValueError("A távolság és a sebesség szám legyen.") from hiba

        if not math.isfinite(tavolsag) or not math.isfinite(maximalis_sebesseg):
            raise ValueError("A távolság és a sebesség véges szám legyen.")
        if tavolsag < 0:
            raise ValueError("A távolság nem lehet negatív.")
        if maximalis_sebesseg <= 0:
            raise ValueError("A maximális sebesség legyen pozitív.")

        return {
            "request_id": request_id,
            "command": "move",
            "distance_m": tavolsag,
            "max_speed": maximalis_sebesseg,
        }

    raise ValueError("Ismeretlen parancs. Használható: observe, move, stop, quit.")


def uzenet_kuldese(
    olvaso: TextIO,
    iro: TextIO,
    keres: dict[str, Any],
    naplo: JsonlNaplo,
) -> bool:
    kuldendo = json.dumps(keres, ensure_ascii=False, separators=(",", ":"))

    try:
        iro.write(kuldendo + "\n")
        iro.flush()
        naplo.rogzit("sent", keres)
        print(f">> {kuldendo}")

        valasz_sor = olvaso.readline()
    except (BrokenPipeError, ConnectionError, OSError) as hiba:
        print(f"A kapcsolat megszakadt: {hiba}", file=sys.stderr)
        return False

    if valasz_sor == "":
        print("A Unity szerver lezárta a kapcsolatot.", file=sys.stderr)
        return False

    valasz_sor = valasz_sor.rstrip("\r\n")

    try:
        valasz = json.loads(valasz_sor)
    except json.JSONDecodeError as hiba:
        naplo.rogzit("received_invalid", {"raw": valasz_sor, "error": str(hiba)})
        print(f"Hibás JSON-válasz: {valasz_sor}", file=sys.stderr)
        return True

    naplo.rogzit("received", valasz)

    if not isinstance(valasz, dict):
        print("Hibás válasz: a legfelső JSON-érték nem objektum.", file=sys.stderr)
    elif valasz.get("request_id") != keres["request_id"]:
        print(
            "Figyelmeztetés: a válasz request_id mezője nem egyezik a kérésével.",
            file=sys.stderr,
        )

    print("<< " + json.dumps(valasz, ensure_ascii=False, indent=2))
    return True


def interaktiv_kliens(host: str, port: int) -> int:
    print(f"Kapcsolódás: {host}:{port} ...")

    try:
        kapcsolat = socket.create_connection((host, port), timeout=5)
        kapcsolat.settimeout(None)
    except (ConnectionError, OSError) as hiba:
        print(f"Nem sikerült kapcsolódni a Unity szerverhez: {hiba}", file=sys.stderr)
        return 1

    print("Kapcsolódva. Parancsok: observe, move <distance> <speed>, stop, quit")

    with JsonlNaplo(NAPLO_FAJL) as naplo, kapcsolat:
        with kapcsolat.makefile("r", encoding="utf-8", newline="\n") as olvaso:
            with kapcsolat.makefile("w", encoding="utf-8", newline="\n") as iro:
                while True:
                    try:
                        beirt_sor = input("gateway> ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print("\nKilépés.")
                        break

                    if beirt_sor.lower() == "quit":
                        print("Kapcsolat lezárva.")
                        break

                    try:
                        keres = parancs_feldolgozasa(beirt_sor)
                    except ValueError as hiba:
                        print(hiba, file=sys.stderr)
                        continue

                    if keres is None:
                        continue

                    if not uzenet_kuldese(olvaso, iro, keres, naplo):
                        break

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Unity RoverGateway TCP kliens")
    parser.add_argument("--host", default=ALAPERTELMEZETT_HOST)
    parser.add_argument("--port", type=int, default=ALAPERTELMEZETT_PORT)
    argumentumok = parser.parse_args()

    if not 1 <= argumentumok.port <= 65535:
        parser.error("A port értéke 1 és 65535 közé essen.")

    return interaktiv_kliens(argumentumok.host, argumentumok.port)


if __name__ == "__main__":
    raise SystemExit(main())
