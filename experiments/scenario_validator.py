#!/usr/bin/env python3
"""Szcenárió JSON fájlok validálása séma és szemantikai szabályok szerint.

Ezt a fájlt Dalma írta kézzel (nem a Codex), mert a hónapos AI-kvóta
elfogyott az M06 mérföldkő munkája közben. A séma, a dokumentáció és a
generátor szkriptek a Codex-szel készültek (lásd AI_USAGE.md).

Használat:
    python3 experiments/scenario_validator.py experiments/scenarios/*.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs" / "scenario.schema.json"


def validate_schema(dokumentum: dict) -> list[str]:
    """JSON Schema alapú ellenőrzés, ha elérhető a jsonschema csomag."""
    hibak: list[str] = []
    try:
        import jsonschema
    except ImportError:
        hibak.append(
            "FIGYELMEZTETÉS: a 'jsonschema' csomag nincs telepítve, "
            "a teljes séma-ellenőrzés kimarad (csak a kézi ellenőrzések futnak). "
            "Telepítés: pip install jsonschema --break-system-packages"
        )
        return hibak

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        sema = json.load(f)

    validator = jsonschema.Draft202012Validator(sema)
    for hiba in validator.iter_errors(dokumentum):
        eleresi_ut = "/".join(str(r) for r in hiba.absolute_path) or "(gyökér)"
        hibak.append(f"Séma hiba ({eleresi_ut}): {hiba.message}")
    return hibak


def validate_semantics(dokumentum: dict) -> list[str]:
    """Szemantikai szabályok, amiket a JSON Schema nem tud kifejezni."""
    hibak: list[str] = []

    # 1. Az akadály-azonosítók legyenek egyediek.
    azonositok = [o.get("id") for o in dokumentum.get("obstacles", [])]
    duplikaltak = {a for a in azonositok if azonositok.count(a) > 1}
    if duplikaltak:
        hibak.append(f"Duplikált akadály-azonosítók: {sorted(duplikaltak)}")

    # 2. disappear_at_s = appear_at_s + visible_for_s (3 tizedesjegy pontossággal).
    for akadaly in dokumentum.get("obstacles", []):
        utemezes = akadaly.get("schedule", {})
        vart = round(utemezes.get("appear_at_s", 0) + utemezes.get("visible_for_s", 0), 3)
        tenyleges = utemezes.get("disappear_at_s")
        if tenyleges is None or abs(vart - tenyleges) > 1e-6:
            hibak.append(
                f"Akadály '{akadaly.get('id')}': disappear_at_s ({tenyleges}) "
                f"nem egyezik appear_at_s + visible_for_s ({vart}) értékkel."
            )

    # 3. Az akadályok legyenek a pálya "burkoló téglatestjén" belül
    #    (durva, de hasznos épség-ellenőrzés - nem pontos geometriai
    #    ráillesztés a stadion alakra).
    track = dokumentum.get("track", {})
    egyenes = track.get("straight_length_m", 0)
    sugar = track.get("turn_radius_m", 0)
    x_hatar = sugar + max(
        o.get("size_m", {}).get("x", 0) for o in dokumentum.get("obstacles", [{"size_m": {}}])
    )
    z_hatar = egyenes / 2 + sugar

    for akadaly in dokumentum.get("obstacles", []):
        pozicio = akadaly.get("position_m", {})
        x, z = pozicio.get("x", 0), pozicio.get("z", 0)
        if abs(x) > x_hatar + 1e-6 or abs(z) > z_hatar + 1e-6:
            hibak.append(
                f"Akadály '{akadaly.get('id')}' pozíciója (x={x}, z={z}) "
                f"kívül esik a pálya becsült burkoló téglatestjén "
                f"(|x|<={x_hatar:.3f}, |z|<={z_hatar:.3f})."
            )

    return hibak


def validate_file(fajl_utvonal: Path) -> bool:
    with open(fajl_utvonal, "r", encoding="utf-8") as f:
        dokumentum = json.load(f)

    sema_hibak = validate_schema(dokumentum)
    szemantikai_hibak = validate_semantics(dokumentum)
    osszes_hiba = sema_hibak + szemantikai_hibak

    if osszes_hiba:
        print(f"❌ {fajl_utvonal.name}: {len(osszes_hiba)} probléma")
        for hiba in osszes_hiba:
            print(f"   - {hiba}")
        return False

    print(f"✅ {fajl_utvonal.name}: érvényes")
    return True


def main() -> None:
    if len(sys.argv) < 2:
        print("Használat: python3 scenario_validator.py <fajl1.json> [fajl2.json ...]")
        sys.exit(1)

    minden_ok = True
    for arg in sys.argv[1:]:
        for fajl in sorted(Path().glob(arg)) if "*" in arg else [Path(arg)]:
            if not validate_file(fajl):
                minden_ok = False

    sys.exit(0 if minden_ok else 1)


if __name__ == "__main__":
    main()
