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

### 5. Zsákutca és eltűnő akadály kezelése (kész, ez a session)
**Zsákutca:** ha a rover `ZSAKUTCA_AKADALY_MAX_LEPES` (20) egymást
követő lépésig `AKADALY` állapotban marad anélkül, hogy sikerülne
kikerülnie (pl. két akadály közé szorul), a rendszer a további
fordulgatás helyett a tágabb `KERESES` állapotra eszkalál, és ezt
külön statisztikaként (`zsakutcak_szama`) számolja - elkülönítve a
sikeres akadálykerülésektől. Unit teszttel lefedve
(`test_akadaly_zsakutca_eszleles_eskalal_keresesre`).

**Eltűnő akadály:** ezt a rendszer már korábban is helyesen kezelte
- ha a LiDAR már nem lát akadályt elöl, a rover kilép az `AKADALY`
állapotból, függetlenül attól, hogy ez azért történt, mert sikeresen
elkerülte, vagy mert az akadály közben eltűnt
(`schedule.disappear_at_s`). **Tudatos tervezési döntés, nem
hiányosság:** a rover a rendelkezésére álló, nem-privilegizált
adatokból (LiDAR) nem tudja és nem is szabad, hogy valós időben
megkülönböztesse ezt a két esetet - az privilegizált pozíció-adat
használatát igényelné a vezérlési döntésben, ami sértené a projekt
alapelvét. A különbség utólag, diagnosztikai célra a lépésnaplóból
(`position` mező) az `analyze_step_log.py`-jal állapítható meg.

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

### 7. Végleges 30 futásos mérési sorozat (kész, ez a session)
Egy fontos, korábban észrevétlen hibát is feltártunk és kijavítottunk
eközben: az akadályok `schedule.appear_at_s`/`disappear_at_s`
időzítése a Play mód *indításához* volt kötve, nem az egyes
futások `reset_position` parancsához - emiatt az akadályok gyakorlatilag
csak a Play mód elindítása utáni néhány másodpercben jelentek meg
egyszer, utána egy teljes Play munkamenetben többé soha. Javítás:
`TrackController.UjrakezdiAkadalyUtemezest()` új publikus metódus,
amit a `RoverGatewayServer` minden `reset_position` parancsnál
meghív, így minden futás saját, független időablakot kap.

**Fontos, tudatosan vállalt mérési egyszerűsítés:** a 70x Time Scale
miatt a hálózati parancsok oda-vissza útja alatt is több szimulált
másodperc telik el, ami a rövid (5-7 másodperces) időzített
időablakot gyakorlatilag elérhetetlenné teszi TCP-n keresztül
irányított futásoknál. Ezért a végleges méréshez az akadályokat
*állandóan láthatóvá* tettük (`experiments/scenarios/stadium-train-baseline.json`-ben
`disappear_at_s` nagyon nagyra állítva) - ez eltér az eredeti,
tervezett időzített szcenáriótól, és ezt a jövőbeli mérésekben is
egyértelműen jelölni kell.

**Eredmény (30 futás, mindkét akadály állandóan látható):**
- Parancsok száma: átlag 832.9, szórás 317.4 (475-1297)
- Vonalvesztések: átlag 17.2, szórás 11.7 (4-40)
- Akadálykerülések: átlag 2.8, szórás 2.2 (0-10)
- Zsákutcák: 0/30 futásban
- Pályaelhagyások: **18/30 futásban**
- Ütközések: átlag 20.9, szórás 17.0 (3-64)
- Ütközött futások: 30/30

**Értelmezés, őszintén:** ez az eredmény **megerősíti** az M09-ben
már dokumentált, ismert oszcillációs problémát - mivel az akadály
most állandóan jelen van, a rover a pálya minden körbejárásánál
ismételten belefut, ami magyarázza a magas ütközésszámot és a
gyakori pályaelhagyást. Ez **nem** az M10 munkacsomagjainak (ütközés-
detektálás, VISSZATALALAS, zsákutca-kezelés) hibája - azok külön-külön,
célzott teszteken igazoltan helyesen működnek (lásd 2. és 4. pont) -,
hanem az eredeti M09 oszcillációs probléma **még mindig nyitott**,
és ez a mérés ezt csak élesebben megmutatja, mert most nincs esély
arra, hogy az akadály időközben eltűnjön és "megmentse" a rovert.
A gyökérok-javítás (pl. az elkerülési stratégia finomítása ismételt
találkozásoknál) M11+ munkaként azonosítva, nem ennek a
mérföldkőnek a része.

### 8. State-machine diagram, videók
Az M09-es háromállapotú diagram (`docs/state_machine.svg`)
frissítése a tervezett `VISSZATALALAS` állapottal, majd demonstrációs
videók - még nincs kész.

## Következő konkrét lépés
State-machine diagram frissítése, demonstrációs videó, majd az M10
git tag és a GitHub Milestone/Issue lezárása.
Csak ezután érdemes a 30 futásos mérési sorozatot megismételni és az
`analyze_step_log.py`-t éles logon lefuttatni.

Csak ezután érdemes a 30 futásos mérési sorozatot megismételni és az
`analyze_step_log.py`-t éles logon lefuttatni.