# Tesztek - lefedettségi összefoglaló

Összesen 29 automatizált teszt + 1 integrációs ellenőrzés. A CI
(`.github/workflows/ci.yml`) a Unity-t nem igénylő 23 tesztet és a
referenciaepizód-ellenőrzést futtatja minden push-nál; a 6 fuzz teszt
élő Unity Play módot igényel, ezért csak helyben fut.

| Fájl | Tesztek | Mit fed le | Regressziós teszt korábbi hibára |
|---|---|---|---|
| `baseline_line_follower_test.py` | 10 | A vonalkövető állapotgép (VONALON / AKADALY / VISSZATALALAS / KERESES) minden átmenete, stub klienssel, Unity nélkül | M10: akadály elhagyása után VISSZATALALAS-ra vált, nem közvetlenül VONALON-ra; zsákutca-eszkaláció KERESES-re `ZSAKUTCA_AKADALY_MAX_LEPES` után; M09: keresés maximuma után pályaelhagyás jelzése |
| `kiserlet_naplo_test.py` | 5 | M11 egységes naplóséma: mezők, több lépés hozzáfűzése, seed nélküli működés, privilegizált diagnosztika alapértéke, két naplózó közös fájlba | - (új modul) |
| `replay_visualizer_test.py` | 4 | Futás betöltése run_id alapján, ütközések jelölése, hiányzó diagnosztika kezelése | M11: a "ragadós" `collision_occurred` mező nem jelölhet minden lépést ütközöttnek - a `collision_count` növekményét kell figyelni (a replay-eszköz fejlesztése közben talált hiba) |
| `scenario_seed_test.py` | 4 | Szcenárió-generálás determinisztikus seedelése; a bejegyzett szcenáriófájl egyezik a generátor kimenetével | M10 audit: a `stadium-train-baseline.json`-t mérés miatt tartósan módosították - ez a teszt azóta megakadályozza, hogy a generátor-hű fájl észrevétlenül megváltozzon |
| `protocol_fuzz_test.py` | 6 (Unity kell) | v1 protokoll: randomizált move/turn tartományok, hibás/csonka JSON, extra/duplikált mezők, idempotencia, MOVING állapotbeli második move (1300-as hibakód) | M05: a fuzz teszt által feltárt két eredeti hiba (szerver-lefagyás csonka JSON-nál, engedékeny validáció) |
| `scripts/referencia_epizod.py` | integrációs | Commitolt 500 lépéses referencia-napló metrikái egyeznek az `elvart.json`-nal, replay-kép elkészül | M11 elfogadási feltétel: referenciaepizód friss klónból |

Futtatás (Unity nélkül):

```bash
python3 tests/baseline_line_follower_test.py -v
python3 tests/kiserlet_naplo_test.py -v
python3 tests/replay_visualizer_test.py -v
python3 tests/scenario_seed_test.py -v
python3 scripts/referencia_epizod.py
```

Ami **nincs** lefedve automatizált teszttel (nyitott, M11 3. munkacsomag):
a Unity-oldali komponensek (`ColorSensor`, `LidarSensor`, `TrackController`,
`RoverGatewayServer` ütközésdetektálás) - ezeket eddig kézi, videóval és
kalibrációs méréssel dokumentált Play módos tesztek fedik (`docs/sensors.md`,
`docs/lidar.md`, `docs/m10-plan.md`).

---

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
