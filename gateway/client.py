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
MAXIMALIS_FRAME_MERET = 16 * 1024
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

    if parancs in {"observe", "get_status", "stop", "reset_error", "reset_position"}:
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
        if not 0.01 <= tavolsag <= 2.00:
            raise ValueError("A distance_m értéke 0.01 és 2.00 méter közé essen.")
        if not 0.05 <= maximalis_sebesseg <= 0.50:
            raise ValueError("A max_speed értéke 0.05 és 0.50 m/s közé essen.")

        return {
            "request_id": request_id,
            "command": "move",
            "distance_m": tavolsag,
            "max_speed": maximalis_sebesseg,
        }

    if parancs == "turn":
        if len(reszek) != 3:
            raise ValueError("Használat: turn <angle_deg> <max_angular_speed>")

        try:
            szog = float(reszek[1])
            maximalis_szogsebesseg = float(reszek[2])
        except ValueError as hiba:
            raise ValueError("A szög és a szögsebesség szám legyen.") from hiba

        if not math.isfinite(szog) or not math.isfinite(maximalis_szogsebesseg):
            raise ValueError("A szög és a szögsebesség véges szám legyen.")
        if not -180 <= szog <= 180 or abs(szog) < 1:
            raise ValueError(
                "Az angle_deg -180 és 180 fok közé essen, "
                "abszolút értéke legalább 1 fok legyen."
            )
        if not 5 <= maximalis_szogsebesseg <= 45:
            raise ValueError(
                "A max_angular_speed értéke 5 és 45 fok/s közé essen."
            )

        return {
            "request_id": request_id,
            "command": "turn",
            "angle_deg": szog,
            "max_angular_speed": maximalis_szogsebesseg,
        }

    raise ValueError(
        "Ismeretlen parancs. Használható: observe, get_status, move, turn, "
        "stop, reset_error, quit."
    )


def pontosan_fogad(kapcsolat: socket.socket, hossz: int) -> bytes | None:
    """Pontosan ``hossz`` bájtot olvas; tiszta EOF esetén None-t ad vissza."""
    reszek: list[bytes] = []
    hatralevo = hossz

    while hatralevo:
        adat = kapcsolat.recv(hatralevo)
        if not adat:
            if hatralevo == hossz:
                return None
            raise ConnectionError("A kapcsolat egy TCP frame közben szakadt meg.")
        reszek.append(adat)
        hatralevo -= len(adat)

    return b"".join(reszek)


def uzenet_kuldese(
    kapcsolat: socket.socket,
    keres: dict[str, Any],
    naplo: JsonlNaplo,
) -> bool:
    kuldendo = json.dumps(keres, ensure_ascii=False, separators=(",", ":"))
    payload = kuldendo.encode("utf-8")

    if not 1 <= len(payload) <= MAXIMALIS_FRAME_MERET:
        print(
            f"A kimenő JSON mérete nem lehet több {MAXIMALIS_FRAME_MERET} bájtnál.",
            file=sys.stderr,
        )
        return True

    try:
        # A 4 bájtos prefix a JSON UTF-8 payload unsigned, big-endian hossza.
        kapcsolat.sendall(len(payload).to_bytes(4, byteorder="big", signed=False))
        kapcsolat.sendall(payload)
        naplo.rogzit("sent", keres)
        print(f">> {kuldendo}")

        hossz_prefix = pontosan_fogad(kapcsolat, 4)
        if hossz_prefix is None:
            print("A Unity szerver lezárta a kapcsolatot.", file=sys.stderr)
            return False

        valasz_hossz = int.from_bytes(hossz_prefix, byteorder="big", signed=False)
        if not 1 <= valasz_hossz <= MAXIMALIS_FRAME_MERET:
            print(
                f"Hibás válaszframe-méret: {valasz_hossz} bájt.",
                file=sys.stderr,
            )
            return False

        valasz_payload = pontosan_fogad(kapcsolat, valasz_hossz)
        if valasz_payload is None:
            print("A Unity szerver lezárta a kapcsolatot.", file=sys.stderr)
            return False
        valasz_szoveg = valasz_payload.decode("utf-8")
    except (BrokenPipeError, ConnectionError, OSError) as hiba:
        print(f"A kapcsolat megszakadt: {hiba}", file=sys.stderr)
        return False
    except UnicodeDecodeError as hiba:
        print(f"A válasz nem érvényes UTF-8: {hiba}", file=sys.stderr)
        return False

    try:
        valasz = json.loads(valasz_szoveg)
    except json.JSONDecodeError as hiba:
        naplo.rogzit("received_invalid", {"raw": valasz_szoveg, "error": str(hiba)})
        print(f"Hibás JSON-válasz: {valasz_szoveg}", file=sys.stderr)
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

    print(
        "Kapcsolódva. Parancsok: observe, get_status, "
        "move <distance_m> <max_speed>, "
        "turn <angle_deg> <max_angular_speed>, stop, reset_error, quit"
    )

    with JsonlNaplo(NAPLO_FAJL) as naplo, kapcsolat:
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

            if not uzenet_kuldese(kapcsolat, keres, naplo):
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
