# M10 terv: akadálykerülés és visszatalálás a vonalra

## Cél

Az M09 baseline kiegészítése **teljes, determinisztikus**
akadálykerüléssel és vonal-visszakereséssel: a rendszer előre
definiált akadályszcenáriók többségében ütközés nélkül térjen
vissza a vonalra, a kudarcokat pedig egy explicit hiba-taxonómia
szerint automatikusan címkézze.

## Kiindulási állapot (M09-ből örökölt)

Az M09 baseline (`controllers/baseline_line_follower.py`) már
tartalmaz egy kezdetleges **AKADÁLY** állapotot: LiDAR-szektor
alapú akadályészlelés hiszterézissel (belépés 0.5 m, kilépés 0.8 m)
és egy fix szögű (45°) elkerülő fordulat a szabadabb oldal felé.
Két 30 futásos mérési sorozat mindkettő 0/30 pályaelhagyással zárult
- a baseline stabil, de a `docs/m09-plan.md` dokumentál egy
**nyitva hagyott, őszintén jelzett problémát**: az akadálykerülések
száma futásonként erősen kétmodális eloszlású (a futások kb.
egyharmada 10-12 ismétlődő akadálytalálkozást mutat), ami arra utal,
hogy bizonyos megközelítési szögeknél az elkerülő fordulat
visszafordítja a rovert ugyanahhoz vagy egy másik akadályhoz -
**oszcillációs ciklus**. Ennek gyökere lépésenkénti naplózás nélkül
nem volt diagnosztizálható.

**Fontos, eddig fel nem ismert dokumentációs/mérési rés**, amit M10
elején pótoltunk:
- `docs/protocol.md` nem dokumentálta a `lidar_szektor_min` mezőt
  (pedig M08 óta az `observe` válasz része) - pótolva.
- A rendszernek **nem volt ütközésdetektálása**: sem a Unity, sem a
  protokoll nem jelezte vissza, ha a rover ténylegesen nekiütközött
  egy akadálynak. Az "akadálykerülések száma" metrika valójában csak
  azt mérte, hányszor lépett AKADÁLY állapotba - nem azt, hogy sikeres
  volt-e a kerülés.

## M10 munkacsomagok

### 1. Lépésenkénti diagnosztikai naplózás (kész)
`controllers/baseline_line_follower.py` új `LepesNaplozo` osztálya
minden lépésnél JSONL-be írja: `run_id`, lépésszám, állapot előtte/
utána, a három vonalszenzor nyers értéke, `lidar_szektor_min`, a
lépésben kiadott parancs(ok), valamint - **kizárólag diagnosztikai
célra, a vezérlési döntésben nem használva** - a privilegizált
`position` és az új `collision_occurred`/`collision_count` mezőket.
Napló helye: `logs/m10_lepes_naplo.jsonl` (`--lepes-naplo` kapcsolóval
állítható vagy kikapcsolható).

### 2. Ütközésdetektálás Unity oldalon (kész)
- `TrackController.FelepitAkadalyokat()`: minden létrehozott akadály
  megkapja az `Akadaly` taget.
- `RoverGatewayServer.cs`: új `OnCollisionEnter` kezelő, ami az
  `Akadaly` taggel ütköző eseményeket számolja
  (`utkozesTortentAzUtolsoResetOta`, `utkozesekSzamaAzUtolsoResetOta`).
  Ezek a `reset_position`/`reset_error` parancsoknál nullázódnak, így
  futásonként tisztán mérhető az ütközésszám.
- `observe` válasz bővítve `collision_occurred`/`collision_count`
  mezőkkel (`docs/protocol.md`-ben dokumentálva, kizárólag
  diagnosztikai célra megjelölve, ahogy a `position`/`speed` is).
- **- **Unity Play módban igazolva:** a rover pozícióját kézzel egy
  mindig aktív teszt-objektum (`TesztAkadaly`, ideiglenesen `Akadaly`
  taggel ellátva) helyére állítva az `OnCollisionEnter` helyesen és
  ismételten lefutott (`M10: utkozes eszlelve...` log-üzenet).
- - **Javítva és igazolva:** a többszörös ütközés-számlálás problémáját
  egy időalapú "hűtési" (cooldown) mechanizmussal orvosoltuk
  (`UtkozesCooldownMasodperc = 0.5f`): egy új ütközés csak akkor
  számít, ha az előzőtől legalább fél másodperc telt el. Az első
  próbálkozás (colliderenkénti be-/kilépés számlálása
  `OnCollisionEnter`/`OnCollisionExit` párral) **nem vált be** - a
  rover több colliderje (alváz + 4 kerék) egyszerre, mélyen átfedésben
  egy akadállyal instabil, oda-vissza ugráló érintkezés-jelzéseket
  produkált a fizikai motorban. Az időalapú megoldást manuálisan
  teszteltük: egy rögzített pozícióban a számláló **nem nőtt tovább**
  több mint két percig, míg a korábbi (hibás) verzióval percenként
  több tucatszor nőtt volna.

### 3. Oszcilláció diagnosztizálása a lépésnaplóból (kész)
Új `controllers/analyze_step_log.py` szkript: futásonként megkeresi az
AKADÁLY-belépéseket, és két egymást követő belépés `position` mezője
alapján (kizárólag diagnosztikai célra) jelzi, ha a rover 0.3 m-nél
kevesebbet haladt előre két akadálytalálkozás között - ez a jel az
M09-ben leírt "ugyanahhoz az akadályhoz visszafordul" jelenségre utal,
szemben azzal, amikor egyszerűen több, egymástól távoli akadállyal
találkozik útközben. Szintetikus naplóval végponttól végpontig
tesztelve (helyben-ismétlődő párt helyesen jelzett, távoli,
egyszeri akadálytalálkozást helyesen nem jelzett gyanúsnak).
**Korlát, amit nem hallgatunk el:** ez csak azt méri, hogy a pozíció
alig változott - nem bizonyítja, hogy ugyanazt az akadályt kerülte-e
a rover ismételten; első, gyors triázs-eszköznek szánjuk, nem végleges
hiba-taxonómia-döntésnek. Éles naplóval (valódi Unity-futásból) még
nincs kipróbálva.

### 4. Explicit vonal-visszakeresési eljárás kerülés után (kész - teszteletlen stratégia)
Új `VISSZATALALAS` állapot: az AKADÁLY állapot már nem közvetlenül
VONALON-ra vált, amint a LiDAR szabadnak jelzi az elülső szektorokat,
hanem a `VISSZATALALAS` állapotba lép. Ott a rendszer megjegyzi az
elkerülő fordulat irányát, és azzal **ellentétes** irányba forog kis
lépésekben (5°-onként), miközben lassan előre halad, amíg valamelyik
vonalszenzor `white`-ot nem jelez. Ha ez `VISSZATALALAS_MAX_LEPES`
(15) lépésen belül nem sikerül, a rendszer a tágabb, általános
KERESÉS állapotra eszkalál.
**Unity Play módban tesztelve (10+1 futás):** 18, teljes 500 lépésig
lefutott, "tiszta" (pályaelhagyás nélküli) futás közül 11-ben
aktiválódott a `VISSZATALALAS` állapot, és mind a 11 esetben
sikeresen visszatalált a vonalra (`VONALON`) - egyetlen eszkalálás
sem történt a tágabb `KERESES` állapotra. **Ez biztató, de a
mintaméret (11 esemény) kicsi** ahhoz, hogy általános
megbízhatóságot állítsunk - nagyobb mintás mérés (a tervezett
végleges 30 futásos sorozat) szükséges a szilárd következtetéshez.

**Módszertani tanulság ebből a tesztelési körből:** egy próbálkozás
során ideiglenesen "örökké láthatóvá" tettük a szcenárió akadályait
(a `disappear_at_s` érték drasztikus megnövelésével) a tesztelés
felgyorsítására - ez viszont torzította a mérést, mert a rover a
pálya körbejárása során ismételten ugyanabba az akadályba futott
bele (17-39 ütközés/futás, gyakori pályaelhagyás), ami nem
reprezentálja a tervezett, időzített szcenáriót. Az eredeti
időzítés visszaállítása után a viselkedés visszatért az M09-cel
konzisztens, egészséges mintázathoz (0 pályaelhagyás mind a 10
futásban).

Az állapotgép mind a négy állapotára és azok átmeneteire új unit
tesztek készültek (`tests/baseline_line_follower_test.py`, 9 teszt,
mind zöld) - stub gateway-klienssel, Unity nélkül futnak. **Nem
helyettesítik** a Unity Play Mode-os fizikai tesztet.

### 5. Zsákutca és eltűnő akadály kezelése (még nincs kész)
A jelenlegi logika nem kezeli explicit módon, ha egy akadály a
kerülés közben eltűnik (`schedule.disappear_at_s`), vagy ha a rover
két akadály közé szorul (zsákutca).

### 6. Hiba-taxonómia (részben megalapozva)
Feladatkiírás szerinti kategóriák: ütközés, elakadás, téves vonal,
timeout, oszcilláció. Az ütközés mérése mostantól megvan (2. pont).
**Nyitott kérdés, amit nem akarunk elhamarkodottan lezárni:** a
rendszernek jelenleg nincs kör-/etap-befejezés detektálása, tehát
minden futás technikailag a `--max-lepes` biztonsági korlátig fut -
emiatt jelenleg **nem lehet megbízhatóan megkülönböztetni** egy
"időtúllépés miatt leállított, egyébként sikeres" futást egy valódi
"elakadás" esettől. Ezt a hiba-taxonómia automatikus kódolása előtt
tisztázni kell (vagy kör-detektálással, vagy explicit sikerességi
kritérium bevezetésével).

### 7. State-machine diagram, videók, benchmark logok
Az M09-es háromállapotú diagram (`docs/state_machine.svg`)
frissítése a tervezett `VISSZATALALAS` állapottal, majd demonstrációs
videók és a végleges benchmark-mérés a dinamikus akadályos
szcenáriókon (`experiments/scenarios/`).

## Következő konkrét lépés
Javítani a többszörös ütközés-számlálás problémáját (lásd 2. pont),
mielőtt bármilyen ütközés-alapú mérésre támaszkodnánk. Utána tesztelni
Unity Play módban az új `VISSZATALALAS` állapot tényleges
viselkedését (4. pont) - csökkenti-e a vonal-visszatalálási időt, és
nem vezet-e be új oszcillációt (pl. ha a heurisztikus feltételezett
irány rendszeresen téves).

Csak ezután érdemes a 30 futásos mérési sorozatot megismételni és az
`analyze_step_log.py`-t éles logon lefuttatni.

Csak ezután érdemes a 30 futásos mérési sorozatot megismételni és az
`analyze_step_log.py`-t éles logon lefuttatni.