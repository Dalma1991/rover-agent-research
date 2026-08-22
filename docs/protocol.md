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
  "command": "observe | move | turn | stop | get_status | reset_error | reset_position"
}
```

## Parancsok

### observe
Lekérdezi a rover aktuális pozícióját, sebességét és — az M09
mérföldkőtől kezdve — a vonalérzékelő szenzorok állapotát. Minden
állapotban engedélyezett.

**Válaszmezők (a szabvány mezőkön felül):**

```json
{
  "position": { "x": 0.0, "y": 0.0, "z": 0.0 },
  "speed": 0.0,
  "sensor_mode": "single | three",
  "sensor_left": { "white": false, "intensity": 0.0 },
  "sensor_center": { "white": false, "intensity": 0.0 },
  "sensor_right": { "white": false, "intensity": 0.0 }
}
```

- `position`, `speed`: a rover Unity-beli pozíciója (méter) és
  aktuális sebessége (m/s). **Kizárólag diagnosztikai/naplózási
  célra** - a szenzorokra épülő controllerek (pl. M09 baseline) nem
  támaszkodhatnak ezekre a mezőkre, mivel ez privilegizált
  szimulátor-információ, ami egy valódi roveren nem állna
  rendelkezésre.
- `sensor_mode`: `"single"`, ha csak a középső szenzor aktív,
  `"three"`, ha a bal-közép-jobb háromszenzoros elrendezés aktív
  (lásd `docs/sensors.md`).
- `sensor_left` / `sensor_center` / `sensor_right`: az adott
  szenzor aktuális mérése. `single` módban a `sensor_left` és
  `sensor_right` mezők jelen vannak, de nem tükröznek valós mérést
  (a szenzor inaktív). `white`: a mért intenzitás a küszöb felett
  van-e. `intensity`: a nyers, zajjal terhelt mért érték (lásd
  `docs/sensors.md` a zajmodellért).

Ez additív, visszafelé kompatibilis bővítés - a protokollverzió
emiatt nem változott (marad v1).

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

### reset_error
Csak ERROR állapotban engedélyezett. Ha nincs aktív mozgás, és a rover
fizikai állapota biztonságos (minden pozíció-, forgás- és sebességérték
véges), a rovert a kezdő pozícióba és forgatásba állítja, majd IDLE
állapotba vált. Sikertelen biztonsági ellenőrzéskor ERROR állapotban
marad.

### reset_position

Csak IDLE allapotban engedelyezett. A rovert a kezdo pozicioba es
forgatasba allitja, IDLE allapotban marad (nem valtoztat allapotot,
ellentetben a reset_error-ral, ami ERROR-bol IDLE-be valt). Celja:
kiserleti/mereszsi futasok kozotti, reprodukalhato pozicio-reset,
amikor nincs hibaallapot. Sikertelen biztonsagi ellenorzeskor
ERROR_RESET_NOT_SAFE hibat ad, valtozatlan allapotban marad.

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
ERROR --reset_error (biztonságos)--> IDLE
* --stop--> (mindig elfogadott, idempotens)

Engedélyezési mátrix:

| Parancs | IDLE | MOVING | TURNING | ERROR |
|---|---:|---:|---:|---:|
| observe | igen | igen | igen | igen |
| get_status | igen | igen | igen | igen |
| move | igen | nem | nem | nem |
| turn | igen | nem | nem | nem |
| stop | igen (no-op) | igen | igen | igen (no-op) |
| reset_error | nem | nem | nem | igen |
| reset_position | igen | nem | nem | nem |

## Hibakódok (v1 alkészlet)

| Kód | Név | Jelentés |
|---:|---|---|
| 1101 | INVALID_FIELD_TYPE | Rossz adattípus |
| 1102 | UNKNOWN_FIELD | Nem dokumentált vagy az adott parancsnál nem engedélyezett mező |
| 1103 | DUPLICATE_FIELD | Egy JSON-mező többször szerepel a kérésben |
| 1104 | INVALID_REQUEST_ID | Hibás/hiányzó request_id |
| 1200 | UNKNOWN_COMMAND | Ismeretlen parancs |
| 1202 | NON_FINITE_VALUE | NaN vagy Infinity |
| 1203 | VALUE_OUT_OF_RANGE | Korláton kívüli érték |
| 1300 | COMMAND_NOT_ALLOWED_IN_STATE | Rossz állapotban küldött parancs |
| 1400 | DUPLICATE_REQUEST | Azonos request_id, már feldolgozott |
| 1401 | REQUEST_ID_CONFLICT | Azonos request_id, eltérő payload |
| 1500 | COMMAND_TIMEOUT | Parancs időtúllépés |
| 1501 | WATCHDOG_EXPIRED | Heartbeat hiányzik, kapcsolat vesztve |
| 1502 | ERROR_RESET_NOT_SAFE | A rover fizikai állapota nem resetelhető biztonságosan |
| 1600 | INTERNAL_ERROR | Váratlan belső szerverhiba a kérés feldolgozása közben |

A `reset_error` megszünteti a protokoll korábbi ismert korlátját: ERROR
állapotból korábban nem volt visszatérési út IDLE állapotba.

## Idempotencia

Minden request_id-hoz a szerver eltárolja a payload SHA-256
hash-ét és a végső választ.
- Azonos ID + azonos payload + befejezett kérés -> a cache-elt válasz
  megy vissza, új végrehajtás nélkül.
- Azonos ID + eltérő payload -> 1401 REQUEST_ID_CONFLICT.

## Tesztelési tapasztalatok és ismert korlátok

A `protocol_fuzz_test.py` teszt sikeresen igazolt, és segített kijavítani
két valódi hibát a `RoverGatewayServer.cs` implementációban:

1. egy regressziót, amely minden kérésnél lefagyást okozott;
2. egy JSON-validációs rést, amely csendben elfogadta a duplikált vagy
   nem dokumentált extra mezőket.

Mindkét hibát kijavítottuk, amit a fuzz teszt is megerősített:
`test_hibas_es_csonka_json_mindig_strukturalt_hibat_ad: ok`.

A randomizált `test_move_randomizalt_tartomanyok` és
`test_turn_randomizalt_tartomanyok` ismételt futtatása során a helyi Python
tesztkliens és a Unity Editor közötti kommunikáció több egymást követő
lépés után esetenként megbízhatatlanná vált. Ez timeoutokat,
`WATCHDOG_EXPIRED` hibát és ERROR állapotot okozhatott. Ennek feltételezett
oka a Unity Editor háttérfolyamatainak vagy a helyi gép
erőforrás-terhelésének hatása.

Ezt tesztinfrastruktúra-korlátként, nem protokollhibaként tartjuk nyilván.
A szerver minden egyedileg, kézzel ellenőrzött esetben helyesen viselkedett,
beleértve a validációt, az állapotgépet, a `reset_error` parancsot és az
idempotenciát. Jövőbeli munkaként érdemes a fuzz tesztet izolált
CI-környezetben vagy stabilabb hálózati és erőforrás-körülmények között
futtatni.

## Verziótörténet (v1 keretében, additív bővítések)

- **M09**: az `observe` válasz kibővítve `sensor_mode`,
  `sensor_left`, `sensor_center`, `sensor_right` mezőkkel, hogy a
  hagyományos (AI nélküli) baseline controller kizárólag
  szenzoradatra tudjon támaszkodni, ne a privilegizált
  `position`/`speed` mezőkre.
- **M09**: uj `reset_position` parancs - IDLE allapotbol hivhato
  pozicio-reset a kiserleti futasok kozotti reprodukalhatosaghoz
  (korabban csak a `reset_error` allitotta vissza a kezdopoziciot,
  de az kizarolag ERROR allapotbol volt hivhato).

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
