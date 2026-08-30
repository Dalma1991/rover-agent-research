# Reprodukálhatóság

Ez a dokumentum lépésről lépésre leírja, hogyan futtatható újra a projekt
jelenlegi állapota egy friss klónból, m01-m06 mérföldkövek szerint.

## 1. Előfeltételek

- **Unity**: 6000.3.20f1 LTS (lásd [ENVIRONMENT.md](ENVIRONMENT.md))
- **Python**: 3.9+ (virtuális környezetben ajánlott)
- **Git**

## 2. Klónozás és ellenőrzés

```bash
git clone https://github.com/Dalma1991/rover-agent-research.git
cd rover-agent-research
./scripts/doctor
```

A `scripts/doctor` ellenőrzi a Python/Git verziót és az alapfájlok meglétét.

## 3. Unity projekt megnyitása

1. Nyisd meg a `unity/` mappát Unity Hub-ból (6000.3.20f1 LTS-szel)
2. Válaszd ki a `TrackScene`-t (M06-M07), vagy a `NetworkControlScene`-t
   (M03-M05 közvetlen gateway-teszteléshez)
3. Nyomj Play-t

## 4. Python gateway kliens

```bash
cd gateway
pip install -r requirements.txt  # ha van; egyébként nincs külső függőség
python3 client.py
```

Interaktív parancsok: `observe`, `move <táv> <sebesség>`, `turn <szög> <szögsebesség>`,
`stop`, `get_status`, `reset_error`, `quit` (lásd [docs/protocol.md](docs/protocol.md)).

## 5. Tesztek futtatása

### Protokoll fuzz/property-based tesztek (M05)

Előfeltétel: a Unity Play mód fusson (`NetworkControlScene` vagy `TrackScene`).

```bash
python3 tests/protocol_fuzz_test.py -v
```

### Szcenárió reprodukálhatósági teszt (M06)

Nem igényel futó Unity-t, tisztán Python.

```bash
python3 tests/scenario_seed_test.py -v
```

### Szcenárió validátor (M06)

```bash
pip install jsonschema
python3 experiments/scenario_validator.py "experiments/scenarios/*.json"
```

## 6. Mérföldkövek és a hozzájuk tartozó fő artifactok

| Mérföldkő | Git tag | Fő fájlok |
|---|---|---|
| M01 | `m01` | `scripts/doctor`, `src/main.py` |
| M02 | `m02` | `unity/Assets/Scripts/MovementController.cs`, `docs/videos/movement-demo.mp4` |
| M03 | `m03` | `unity/Assets/Scripts/RoverGatewayServer.cs` (v0), `gateway/client.py` |
| M04 | `m04` | `unity/Assets/Prefabs/RoverChassis.prefab`, `docs/coordinate-system.md` |
| M05 | `m05` | `docs/protocol.md`, `unity/Assets/Scripts/RoverGatewayServer.cs` (v1), `tests/protocol_fuzz_test.py`, `docs/state_machine.svg` |
| M06 | `m06` | `docs/scenario.schema.json`, `docs/scenario-schema.md`, `scripts/generate_scenario_seed.py`, `scripts/generate_example_scenarios.py`, `experiments/scenario_validator.py`, `experiments/scenarios/*.json`, `tests/scenario_seed_test.py`, `unity/Assets/Scripts/TrackController.cs`, `docs/screenshots/m06-*.png` |

Egy adott mérföldkő állapotának pontos visszaállításához:

```bash
git checkout m05   # vagy m01, m02, ..., m06
```

## 7. Ismert korlátok

- A `protocol_fuzz_test.py` élő Unity-kapcsolatra támaszkodó tesztjei
  időnként megbízhatatlanná válnak (socket timeout) helyi hálózati/
  erőforrás-terhelés miatt - ez tesztinfrastruktúra-korlát, nem
  protokollhiba (lásd [AI_USAGE.md](AI_USAGE.md)). Eredetileg csak a
  `test_move_randomizalt_tartomanyok` és `test_turn_randomizalt_tartomanyok`
  teszteknél figyeltük meg ezt (M05), de egy M11-es futtatáskor
  fordítva történt: pont ez a két teszt futott le sikeresen, míg a
  `setUp()`-ban `reset_error` parancsra váró többi teszt bukott
  timeout-tal - vagyis a jelenség általánosabb, mint az eredeti
  megfigyelés sugallta, és bármelyik, hálózati választ váró tesztet
  érintheti.
- A Codex (JetBrains AI Assistant) havi kvótája M06 közben kimerült; az érintett
  fájlokat (`experiments/scenario_validator.py`, `tests/scenario_seed_test.py`,
  `unity/Assets/Scripts/TrackController.cs`) Claude írta, ez az `AI_USAGE.md`-ben
  dokumentálva van.
