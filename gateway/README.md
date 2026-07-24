# Unity gateway CLI kliens

A `client.py` TCP-kapcsolaton és newline-delimited JSON (JSONL/NDJSON) üzeneteken keresztül kommunikál a Unity-ben futó `RoverGatewayServer` komponenssel.

## Követelmények

- Python 3.9 vagy újabb
- A Unity jelenetben aktív `RoverGatewayServer`
- Alapértelmezés szerint a szerver a `127.0.0.1:8765` címen figyel

A kliens kizárólag a Python standard könyvtárát használja, ezért nincs telepítendő Python-csomag.

## Futtatás

A repository gyökérkönyvtárából:

```bash
python3 gateway/client.py
```

Egyedi cím vagy port használata:

```bash
python3 gateway/client.py --host 127.0.0.1 --port 8765
```

## Parancsok

| Parancs | Leírás |
| --- | --- |
| `observe` | Lekéri a gömb aktuális pozícióját és sebességét. |
| `move <distance_m> <max_speed>` | Előremozgatja a gömböt a megadott méterrel és maximális sebességgel. |
| `stop` | Megállítja a gömb mozgását. |
| `quit` | Lezárja a kapcsolatot és kilép a kliensből. |

Például:

```text
gateway> observe
gateway> move 5 2
gateway> stop
gateway> quit
```

Minden elküldött kérés egy UUID-alapú `request_id` mezőt kap. A kliens ellenőrzi, hogy a válaszban ugyanez az azonosító szerepel-e.

## Naplózás

A küldött és fogadott üzenetek időbélyeggel, soronként külön JSON-objektumként ide kerülnek:

```text
gateway/logs/session.jsonl
```

A naplófájl és a `logs` könyvtár az első futtatáskor automatikusan létrejön.
