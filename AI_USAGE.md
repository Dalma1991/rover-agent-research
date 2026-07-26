# AI eszközök használata

## Codex (CLI/IDE integráció)
- **Eszköz:** Codex, PyCharm IDE-integráció
- **Cél:** kódrészletek generálása és kipróbálása

## Elvégzett próbafeladatok

### 1. Prímszám-ellenőrzés
A Codex-szel generáltattam egy `prim_e()` függvényt, ami eldönti egy számról,
hogy prímszám-e. A kódot néhány teszt-számmal (1, 2, 7, 17, 20, 25) ki is
próbáltam.

### 2. Mérési adatok kiértékelése
A Codex-szel generáltattam egy `meresek_kiertékelese()` függvényt, ami egy
számlistából (pl. testhőmérséklet-adatok) kiszámolja az átlagot, a minimumot
és a maximumot, majd szépen kiírja az eredményt.

### 3. CSV-fájl beolvasása
A Codex-szel generáltattam egy `csv_elso_sorai()` függvényt, ami beolvas egy
CSV-fájlt, kiírja az oszlopneveket, majd megjeleníti az első 5 adatsort.
Hibakezelést is tartalmaz (pl. ha a fájl nem található).

### 4. Telepítési ellenőrzőlista (INSTALL_CHECKLIST.md)
A Codex-szel generáltattam egy lépésről lépésre követhető, kipipálható telepítési
ellenőrzőlistát, ami leírja a Git, Unity 6000.3.20f1 LTS és Python 3.9 telepítését,
a virtuális környezet létrehozását, valamint a `scripts/doctor` futtatását
ellenőrzésképp. A listát friss klónból végig is teszteltem.

### 5. scripts/doctor bővítése
A Codex-szel generáltattam egy `scripts/doctor` nevű ellenőrző szkriptet, ami
kiírja a Python, Git és Pip verzióját, ellenőrzi a szükséges Python modulokat
(argparse, csv), és megnézi, hogy a projekt alapfájljai (src/main.py, README.md,
AI_USAGE.md) megvannak-e.

### 6. Unity mozgó gömb komponens (MovementController.cs)
A Codex-szel megíratattam a MovementController.cs C# komponenst, ami a
WASD/nyílbillentyűkkel mozgatja a gömböt egy Rigidbody segítségével.
A komponens tartalmaz egy Inspectorból állítható sebességparamétert,
egy R billentyűre aktiválódó reset funkciót, és egyszerű ütközésjelzést.
A Codex részletesen elmagyarázta a MonoBehaviour, Update és FixedUpdate
szerepét: a bemenet olvasása az Update-ben történik (képkockánként fut),
míg a fizikai mozgatás a FixedUpdate-ben (rögzített időközönként, a
Unity fizikai motorjához igazodva).

### 7. Play Mode tesztek
A Codex 3 lehetséges tesztelési megközelítést javasolt a mozgás és a
reset ellenőrzésére: (1) publikus metódus közvetlen tesztelése,
(2) bemeneti rendszer szimulálása, (3) Rigidbody közvetlen tesztelése.
A publikus metódus (Move()) közvetlen tesztelése mellett döntöttem,
mert stabil, gyors és nem függ az Input System konfigurációjától.
A Codex ez alapján megírta a MovementControllerPlayModeTests.cs
fájlt, ami két tesztet tartalmaz: a mozgás- és a reset-funkció
ellenőrzését. Mindkét teszt sikeresen lefutott.

### 8. TCP/JSON rover gateway szerver (RoverGatewayServer.cs)
A Codex-szel megíratattam egy Unity C# TCP szervert, ami külön háttérszálon
figyel egy portot (127.0.0.1:8765), és newline-delimited JSON üzeneteket
fogad (observe, move, stop parancsok, request_id azonosítóval). A hálózati
szál és a Unity fő szála közötti biztonságos kommunikációt egy
ConcurrentQueue és ManualResetEventSlim párossal oldotta meg — a tényleges
Rigidbody-műveletek mindig a FixedUpdate-ben, a fő szálon futnak.

### 9. Python CLI kliens (gateway/client.py)
A Codex-szel megíratattam egy interaktív Python parancssori klienst, ami
csatlakozik a Unity szerverhez, UUID-alapú request_id-kat generál, és
JSONL fájlba naplózza a kérés-válasz párokat.

### Hibakeresés
A tesztelés során két hibát találtam és javítottam:
1. A gömb nem mozgott annak ellenére, hogy a szerver "elfogadta" a
   parancsot — kiderült, hogy a korábbi MovementController script még
   engedélyezve volt ugyanazon a GameObjecten, és minden FixedUpdate-ben
   nulla elmozdulással felülírta a RoverGatewayServer mozgatását.
   Megoldás: a MovementController letiltása ebben a jelenetben.
2. A "stop" parancs figyelmeztetést dobott ("Setting linear velocity of
   a kinematic body is not supported"), mert a Rigidbody kinematikus
   (MovePosition-t használ), így nem lehet rajta közvetlenül sebességet
   beállítani. Megoldás: a felesleges linearVelocity/angularVelocity
   beállítások eltávolítása a stop ágból — a mozgás leállításához elég
   a hátralévő távolság és sebesség nullázása.

   ### 10. Rovermozgás-modell összehasonlítás
A Codex-től kértem egy összehasonlítást a kinematikus és a WheelCollider-
alapú mozgásmodell között (m04 kötelező AI-használat). A kinematikus
modellt választottam, mert gyors, determinisztikus, könnyen
hibakereshető, és a fejlesztés jelenlegi fázisában (AI-vezérlés és
interfészek kialakítása) ez a fontosabb szempont, nem a fizikai
realizmus. A Codex azt is javasolta, hogy a vezérlés ne Unity-specifikus
parancsokkal, hanem absztrakt sebesség-parancsokkal (linear_velocity_mps,
angular_velocity_radps) történjen, hogy később könnyebben átvihető
legyen WheelCollider-re vagy fizikai roverre — ezt a döntést a
docs/coordinate-system.md fájlban dokumentáltam.

## Tesztelési tapasztalatok és ismert korlátok

A `protocol_fuzz_test.py` sikeresen igazolt, és segített kijavítani két
valódi hibát a `RoverGatewayServer.cs` fájlban: egy regressziót, amely minden
kérésnél lefagyást okozott, valamint egy JSON-validációs rést, amely
csendben elfogadta a duplikált vagy nem dokumentált extra mezőket. Mindkét
hibát kijavítottuk, amit a fuzz teszt is megerősített:
`test_hibas_es_csonka_json_mindig_strukturalt_hibat_ad: ok`.

A randomizált `test_move_randomizalt_tartomanyok` és
`test_turn_randomizalt_tartomanyok` futtatása során ugyanakkor többször
megbízhatatlanná vált a helyi Python tesztkliens és a Unity Editor közötti
kommunikáció, jellemzően több egymást követő lépés után. A timeoutok
`WATCHDOG_EXPIRED` hibát és ERROR állapotot eredményeztek. A jelenség
feltételezett oka a Unity Editor háttérfolyamatainak vagy a helyi gép
erőforrás-terhelésének hatása.

Ezt tesztinfrastruktúra-korlátként, nem protokollhibaként dokumentáljuk.
A szerver minden egyedileg, kézzel tesztelt esetben helyesen viselkedett a
validáció, az állapotgép, a `reset_error` és az idempotencia tekintetében.
Jövőbeli munkaként érdemes a fuzz tesztet izolált CI-környezetben vagy
stabilabb hálózati és erőforrás-körülmények között futtatni.

### 11. Protokoll-review támadói/hibakereső szemszögből (M05 kötelező AI-használat)
A Codex-től kértem egy protokoll-review-t a RoverGatewayServer.cs jelenlegi
implementációjáról, kifejezetten támadói és hibakereső szemszögből. A Codex
felsorolta a lehetséges visszaéléseket (végtelen/túl nagy mozgásparancsok,
NaN/Infinity értékek, request_id ismétlés, gyors egymás utáni parancsok,
kapcsolatbontás menet közben), konkrét számszerű korlátokat javasolt
(sebesség, távolság, szög, timeout, watchdog), egy formális állapotgépet
(IDLE/MOVING/TURNING/ERROR), egy hibakód-rendszert, és egy idempotencia-
megoldást. Ez alapján terveztük meg és dokumentáltuk a docs/protocol.md
fájlban a v1 protokollt.

Az 5 kiemelt prioritást valósítottam meg (véges számok + validáció,
állapotgép, watchdog, idempotencia, frame/rate limit) a teljes javasolt
security-csomag (TLS, control lease, teljes audit-napló) helyett, mivel ez
egy lokális kutatási prototípus, és ezt a döntést a docs/protocol.md
"Tudatosan elhalasztott elemek" szakaszában dokumentáltam.

### 12. Protokoll implementáció és hibajavítás
A Codex implementálta a turn és get_status parancsokat, az állapotgépet,
a szigorú validációt, az idempotencia-cache-t, a reset_error parancsot,
valamint a dinamikus timeout-számítást a fuzz tesztekhez. Egy köztes
lépésben a Codex regressziót vezetett be (minden kérés lefagyott), amit
ő maga azonosított és javított egy try-catch védelemmel és részletes
naplózással.

## Megjegyzések
Az AI (Codex) által generált kódot mindegyik esetben átnéztem és kipróbáltam,
mielőtt bekerült a `src/main.py` fájlba.
