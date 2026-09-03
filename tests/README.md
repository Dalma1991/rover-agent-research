[![CI](https://github.com/Dalma1991/rover-agent-research/actions/workflows/ci.yml/badge.svg)](https://github.com/Dalma1991/rover-agent-research/actions/workflows/ci.yml)

# Rover Gateway v1 fuzz tesztek

A `protocol_fuzz_test.py` a futó Unity Play Mode szervert TCP-n, a v1
4 bájtos big-endian hossz-prefixes protokollon keresztül teszteli.

## Előfeltételek

1. Nyisd meg a `unity/` projektet Unityben.
2. Indítsd el a `NetworkControlScene` jelenetet Play Mode-ban.
3. Ellenőrizd, hogy a gateway a `127.0.0.1:8765` címen figyel.

## Futtatás

A tesztek csak a Python standard libraryt igénylik:

```bash
python3 tests/protocol_fuzz_test.py
```

Ha telepítve van a pytest, ugyanazok a tesztek azzal is futtathatók:

```bash
python3 -m pytest -v tests/protocol_fuzz_test.py
```

A szerver hiányakor a teljes tesztosztály skip státuszt kap. Egy sikertelen
teszt után érdemes újraindítani a Play Mode-ot, ha a rover `ERROR` állapotban
maradt.

## Beállítások

Környezeti változókkal felülírható:

- `ROVER_GATEWAY_HOST` (alapérték: `127.0.0.1`)
- `ROVER_GATEWAY_PORT` (alapérték: `8765`)
- `ROVER_GATEWAY_FUZZ_TIMEOUT` (alapérték: `2` másodperc)
- `ROVER_GATEWAY_FUZZ_CASES` (alapérték: `30` random eset/parancs)
- `ROVER_GATEWAY_FUZZ_SEED` (alapérték: `20260726`)

Gyors smoke futtatás:

```bash
ROVER_GATEWAY_FUZZ_CASES=5 python3 tests/protocol_fuzz_test.py
```

A seed kiírt/alapértelmezett értékével a randomizált esetek reprodukálhatók.
