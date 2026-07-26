# Rover vezérlési protokoll (v1)

## Áttekintés

TCP-kapcsolaton keresztüli, hossz-prefixelt, JSON-alapú protokoll a
rover vezérléséhez. Ez a dokumentum az M05 mérföldkőnél lefagyasztott
v1 protokollt írja le.

**Protokollverzió:** 1

## Kötelező mezők minden kérésben

```json
{
  "request_id": "UUID v4, 36 karakter",
  "command": "observe | move | turn | stop | get_status"
}
```

## Parancsok

### observe
Lekérdezi a rover aktuális pozícióját és sebességét. Minden állapotban
engedélyezett.

### get_status
Lekérdezi a rover jelenlegi állapotát (state machine állapota,
protokollverzió, utolsó parancs eredménye). Minden állapotban
engedélyezett.

### move
Előre/hátra mozgatja a rovert megadott távolsággal és sebességgel.
Csak IDLE állapotban engedélyezett.

Paraméterek:
- `distance_m`: `0.01 - 2.00` (méter)
- `max_speed`: `0.05 - 0.50` (m/s)

### turn
Elforgatja a rovert megadott szöggel. Csak IDLE állapotban engedélyezett.

Paraméterek:
- `angle_deg`: `-180 - 180`, `abs(angle_deg) >= 1`
- `max_angular_speed`: `5 - 45` (fok/s)

### stop
Azonnal leállítja a rovert. Minden állapotban elfogadott, idempotens
(no-op, ha már áll).

## Válaszformátum

```json
{
  "request_id": "...",
  "status": "accepted | completed | failed",
  "state": "IDLE | MOVING | TURNING | ERROR",
  "error": null
}
```

Hiba esetén:
```json
{
  "request_id": "...",
  "status": "failed",
  "state": "IDLE",
  "error": {
    "code": 1203,
    "name": "VALUE_OUT_OF_RANGE",
    "message": "distance_m must be between 0.01 and 2.00"
  }
}
```

## Korlátok (v1)

| Paraméter | Minimum | Maximum |
|---|---:|---:|
| move distance_m | 0.01 m | 2.00 m |
| move max_speed | 0.05 m/s | 0.50 m/s |
| turn angle_deg | 1° (abs) | 180° (abs) |
| turn max_angular_speed | 5°/s | 45°/s |
| Parancs timeout | - | 15 s |
| Watchdog timeout | - | 1 s (3 kihagyott heartbeat) |
| TCP frame méret | - | 16 KiB |
| Kérések/s/kliens | - | 10 (burst 20) |
| Feldolgozatlan kérések sora | - | 32 |

Minden numerikus mezőt véges számnak kell lennie
(NaN/Infinity elutasítva) és a fenti tartományon belülinek -
tartományon kívüli vagy nem véges érték error-t eredményez, nem
csendes korlátozást (nincs "clamp").

## Állapotgép
IDLE --move--> MOVING --siker--> IDLE
IDLE --turn--> TURNING --siker--> IDLE
(MOVING|TURNING) --stop--> IDLE
(MOVING|TURNING) --timeout/hiba--> ERROR
* --stop--> (mindig elfogadott, idempotens)

Engedélyezési mátrix:

| Parancs | IDLE | MOVING | TURNING | ERROR |
|---|---:|---:|---:|---:|
| observe | igen | igen | igen | igen |
| get_status | igen | igen | igen | igen |
| move | igen | nem | nem | nem |
| turn | igen | nem | nem | nem |
| stop | igen (no-op) | igen | igen | igen (no-op) |

## Hibakódok (v1 alkészlet)

| Kód | Név | Jelentés |
|---:|---|---|
| 1101 | INVALID_FIELD_TYPE | Rossz adattípus |
| 1104 | INVALID_REQUEST_ID | Hibás/hiányzó request_id |
| 1200 | UNKNOWN_COMMAND | Ismeretlen parancs |
| 1202 | NON_FINITE_VALUE | NaN vagy Infinity |
| 1203 | VALUE_OUT_OF_RANGE | Korláton kívüli érték |
| 1300 | COMMAND_NOT_ALLOWED_IN_STATE | Rossz állapotban küldött parancs |
| 1400 | DUPLICATE_REQUEST | Azonos request_id, már feldolgozott |
| 1401 | REQUEST_ID_CONFLICT | Azonos request_id, eltérő payload |
| 1500 | COMMAND_TIMEOUT | Parancs időtúllépés |
| 1501 | WATCHDOG_EXPIRED | Heartbeat hiányzik, kapcsolat vesztve |

## Idempotencia

Minden request_id-hoz a szerver eltárolja a payload SHA-256
hash-ét és a végső választ.
- Azonos ID + azonos payload + befejezett kérés -> a cache-elt válasz
  megy vissza, új végrehajtás nélkül.
- Azonos ID + eltérő payload -> 1401 REQUEST_ID_CONFLICT.

## Tudatosan elhalasztott elemek (jövőbeli munka)

A következő elemeket a Codex protokoll-review-ja javasolta, de az
M05 mérföldkőnél tudatosan NEM valósítottuk meg, mert a jelenlegi
fejlesztési fázisban (lokális, egyjátékos kutatási prototípus,
kizárólag 127.0.0.1-en futó szerver) nem indokolt a többletköltségük:

- **TLS/hitelesítés** - csak akkor válik szükségessé, ha a szerver
  külső hálózatra nyílik (pl. távoli fizikai roverhez kapcsolódás).
- **Control lease (kliens-tulajdonjog)** - csak több egyidejű
  vezérlő kliens esetén releváns; jelenleg egyszerre csak egy
  kliens (a Python CLI vagy egy AI agent) vezérel.
- **Teljes audit-napló, kliensazonosítás** - később, ha a rendszer
  többfelhasználós vagy fizikai roverre kerül, érdemes bővíteni.

Ezeket újra kell értékelni, mielőtt a rendszer külső hálózatra
nyílik vagy fizikai roverre kerül.
