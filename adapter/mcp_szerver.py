"""MCP-szerver a rover vezerlesehez (M12, 3. munkacsomag).

Az agent (Claude Code) ezen a hat eszkozon keresztul latja a rovert:
observe, move, turn, stop, reset_position, session_status.

Amit az agent NEM kap meg:
- shell- vagy fajlrendszer-hozzaferest,
- a Unity szimulator privilegizalt mezoit (pozicio, sebesseg, utkozesszamlalo),
- a v1 protokoll tovabbi parancsait (get_status, reset_error),
- azt az informaciot, hogy valodi Unity-szimulacio vagy mock all mogotte.

Inditas (a projekt Python 3.9-es venv-je erintetlen marad):
    uv run --python 3.12 --with mcp python adapter/mcp_szerver.py --backend mock
    uv run --python 3.12 --with mcp python adapter/mcp_szerver.py --backend unity

A --backend valasztas a kiserletvezetoe, nem az agente; az agent szamara a
ket eset megkulonboztethetetlen.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adapter.backend import MockAkadaly, MockBackend, UnityTcpBackend  # noqa: E402
from adapter.orseg import Orseg, SessionKorlatok  # noqa: E402

from mcp.server.mcpserver import MCPServer  # noqa: E402

_orseg: Orseg | None = None

szerver = MCPServer(
    name="rover",
    version="0.12.0",
    instructions=(
        "Egy vonalkoveto rover vezerlese egy stadion alaku palyan. "
        "A rover harom szinszenzorral (bal/kozep/jobb) latja a feher vonalat, "
        "es egy 6 szektoros Lidarral az akadalyokat. Minden lepesnel eloszor "
        "hivj observe-ot, majd dontsd el a kovetkezo move/turn parancsot. "
        "A munkamenet korlatozott (parancsszam, ido, ossztavolsag): a "
        "session_status megmutatja, mennyi maradt. Nincs hozzaferesed a rover "
        "valos pozciojahoz - csak a szenzorokra tamaszkodhatsz."
    ),
)


def orseg() -> Orseg:
    if _orseg is None:
        raise RuntimeError("Az adapter nincs inicializalva.")
    return _orseg


@szerver.tool(
    description=(
        "Leolvassa a rover szenzorait. Visszaadja a harom szinszenzort "
        "(sensor_left, sensor_center, sensor_right; mindegyik 'white' logikai "
        "es 'intensity' 0-1 ertekkel), valamint a lidar_szektor_min listat: 6 "
        "szektor legkozelebbi akadalytavolsaga meterben, balrol jobbra, a "
        "rover elotti 180 fokos legyezoben (10.0 = nincs akadaly hatotavon "
        "belul). Minden allapotban hivhato, nem mozgatja a rovert."
    )
)
def observe() -> dict[str, Any]:
    return orseg().observe()


@szerver.tool(
    description=(
        "Elore mozgatja a rovert. distance_m: 0.01-1.00 meter. max_speed: "
        "0.05-0.50 m/s (alapertelmezett 0.2). A parancs a mozgas "
        "befejezesekor ter vissza. Tartomanyon kivuli vagy nem szamertek "
        "eseten a hivas elutasitasra kerul (status: rejected), a rover nem "
        "mozdul. A munkamenet ossztavolsag-kerete is korlatozza."
    )
)
def move(distance_m: float, max_speed: float = 0.2) -> dict[str, Any]:
    return orseg().move(distance_m, max_speed)


@szerver.tool(
    description=(
        "Elforgatja a rovert a helyben. angle_deg: -180 es 180 kozott, az "
        "abszolut erteke legalabb 1; pozitiv = jobbra, negativ = balra. "
        "max_angular_speed: 5-45 fok/s (alapertelmezett 30). Tartomanyon "
        "kivuli ertek eseten a hivas elutasitasra kerul, a rover nem mozdul."
    )
)
def turn(angle_deg: float, max_angular_speed: float = 30.0) -> dict[str, Any]:
    return orseg().turn(angle_deg, max_angular_speed)


@szerver.tool(
    description=(
        "Azonnal leallitja a rovert. Barmikor hivhato, idempotens (ha mar all, "
        "nem tortenik semmi). Lezart munkamenetben is mukodik."
    )
)
def stop() -> dict[str, Any]:
    return orseg().stop()


@szerver.tool(
    description=(
        "Visszaallitja a rovert a kezdo pozicioba es iranyba. Kiserleti "
        "futasok kozott hasznalatos, hogy minden futas azonos allapotbol "
        "induljon. Csak allo roveren mukodik."
    )
)
def reset_position() -> dict[str, Any]:
    return orseg().reset_position()


@szerver.tool(
    description=(
        "Megmutatja a munkamenet felhasznalt es maximalis kereteit: "
        "parancsszam, eltelt ido, megtett ossztavolsag, egy move maximalis "
        "hossza, elutasitott hivasok szama, valamint hogy a munkamenet le "
        "van-e mar zarva es miert. Nem szamit bele a parancskeretbe."
    )
)
def session_status() -> dict[str, Any]:
    return orseg().session_status()


def parancssor() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Rover MCP-szerver (M12)")
    p.add_argument(
        "--backend", choices=("mock", "unity"), default=os.environ.get("ROVER_BACKEND", "mock")
    )
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--max-parancs", type=int, default=300)
    p.add_argument("--max-ido-s", type=float, default=900.0)
    p.add_argument("--max-tavolsag-m", type=float, default=60.0)
    p.add_argument("--mock-akadalyokkal", action="store_true", help="Mock backend ket akadallyal.")
    return p.parse_args()


def main() -> int:
    global _orseg
    args = parancssor()
    if args.backend == "unity":
        backend = UnityTcpBackend(args.host, args.port)
    else:
        akadalyok = (
            [MockAkadaly(x=4.0, z=3.0), MockAkadaly(x=3.6, z=8.5)] if args.mock_akadalyokkal else []
        )
        backend = MockBackend(akadalyok=akadalyok)
    _orseg = Orseg(
        backend,
        SessionKorlatok(
            max_parancs=args.max_parancs,
            max_idotartam_s=args.max_ido_s,
            max_ossz_tavolsag_m=args.max_tavolsag_m,
        ),
    )
    # A backend tipusa csak a szerver stderr-jere kerul (a kiserletvezetonek),
    # az MCP-csatornara soha - az agent nem tudhatja meg.
    print(f"[rover-mcp] backend={args.backend} korlatok={_orseg.korlatok}", file=sys.stderr)
    szerver.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
