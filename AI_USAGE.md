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

### 13. Szcenárió-séma, generátor és dokumentáció (M06 kötelező AI-használat)
A Codex-től kértem egy JSON sémát egy zárt, stadion alakú rover-pálya
leírásához (geometria, akadályok, seedelt ütemezés), egy generátor
szkriptet, ami determinisztikusan (SHA-256 alapú, platformfüggetlen
módon) állítja elő a train/dev/test példaszcenáriókat, valamint
dokumentációt (docs/scenario-schema.md). A seedeket a Codex tudatosan
nem "kézzel kitalálva" adta meg, hanem egy dokumentált, reprodukálható
segédszkripttel generálta a szcenárió stabil azonosítójából - ezzel
teljesítve a feladat azon megkötését, hogy a teszt seedek ne kerüljenek
"bele" a promptpéldákba.

**Fontos korlát**: a hónapos Codex-kvóta (JetBrains AI) elfogyott menet
közben, mielőtt a validátor és a reprodukálhatósági teszt elkészült
volna. Ezt a két fájlt (experiments/scenario_validator.py,
tests/scenario_seed_test.py), valamint a Unity pálya-építő scriptet
(unity/Assets/Scripts/TrackController.cs) emiatt kézzel írtam meg,
Claude segítségével, Codex nélkül - a Codex által lefektetett séma és
generálási logika pontos ismeretében, hogy a kimenet konzisztens
maradjon. Ezt azért fontos dokumentálni, mert az M06 kötelező
AI-használati elemét (validátor) végül nem AI készítette.

A validátor és a reprodukálhatósági teszt mindegyike lefutott és
sikeres: mind a 3 példaszcenárió érvényes a JSON Schema szerint, és a
reprodukálhatósági teszt igazolta, hogy azonos (típus, név) pár mindig
azonos seedet és azonos akadálysorozatot ad.

### 14. Szenzorkalibráció és háromszenzoros mód (M07 kötelező AI-használat)
A Claude-tól kértem segítséget az M07 mérföldkőhöz: a ColorSensor.cs
kalibrációjának elemzéséhez (5 ismert pozícióban mért intenzitásérték
kiértékelése, a 0.5-ös alapértelmezett küszöb mérés alapú igazolása),
valamint a háromszenzoros (bal-közép-jobb) elrendezés
megtervezéséhez és megírásához. A Claude megírta a SensorArray.cs
komponenst, amely egy kapcsolható (Inspectorban és kódból is
átállítható) haromSzenzorosMod mezővel aktiválja/deaktiválja a bal
és jobb szenzor GameObject-jét, míg a középső mindig aktív marad. A
munka során előkerült egy már meglévő hiba is: a TrackController.cs
két helyen a `.material` property-t használta `.sharedMaterial`
helyett, ami Edit módban anyag-szivárgáshoz vezetett volna — ezt is
a Claude segítségével javítottuk. A háromszenzoros mód helyes,
differenciált működését a pálya kanyarjában végzett kézi teszttel
igazoltam: a három szenzor egyidejűleg eltérő kimenetet adott
(I=0.00 not_white, I=0.12 not_white, I=1.00 WHITE), lásd
docs/sensors.md.

### 15. LiDAR-szimuláció, kalibráció és profilozás (M08 kötelező AI-használat)
A Claude-tól kértem segítséget az M08 mérföldkőhöz: a LidarSensor.cs
megtervezéséhez és megírásához (raycast-alapú, konfigurálható
látómezejű/felbontású 2D LiDAR-modell, szektoros tömörítéssel, zaj-,
dropout- és késleltetés-modellezéssel), valamint a geometriai
kalibráció és a futásidő-profilozás terveinek kidolgozásához. A
kalibráció két lépésben zajlott: előbb egy elvi, transzformáció
nélküli tesztobjektumon (hogy kiküszöböljük a RoverChassis összetett
skálázásából eredő zavaró tényezőket), majd megismételve közvetlenül
a RoverChassis-on lévő éles Lidar komponensen is, ismert
világkoordinátás pozíciókban elhelyezett tesztakadállyal. Mind az öt
mérési pont (0.5/1.5/2.5/4.5/7.5 m elvárt felület-távolság) a 0.02
m-es beállított zaj-szórás ésszerű tartományán belül teljesült,
mindkét tesztsorozatban. A futásidő-profilozás négy felbontásnál
(12/36/72/144 sugár) 0.040–0.239 ms közötti, közel lineárisan
skálázódó mérési időt igazolt. A munka során felmerült egy
self-collision probléma is (a Lidar a rover saját dobozütközőjébe
ütközött) — ezt egy külön "Rover" Unity-réteg bevezetésével és az
Akadaly Reteg mezőből való kizárásával oldottuk meg. Lásd
docs/lidar.md.

### 16. Az observe válasz bővítése szenzoradatokkal (M09 előkészítés, kötelező AI-használat)
Az M09 mérföldkő (hagyományos, AI nélküli vonalkövető baseline)
tervezése közben felmerült, hogy az `observe` parancs válasza addig
kizárólag a rover Unity-beli `position` és `speed` mezőit adta
vissza — ezekre a baseline controller nem támaszkodhat, mivel egy
valódi roveren nem állna rendelkezésre ilyen privilegizált
szimulátor-információ. A Claude-tól kértem segítséget a
RoverGatewayServer.cs observe válaszának kibővítéséhez: a szerver
mostantól a SensorArray komponensből kiolvasva `sensor_mode`
(single/three) és `sensor_left`/`sensor_center`/`sensor_right`
mezőket is visszaad, mindegyiket a saját `white`/`intensity`
értékével. A bővítés additív és visszafelé kompatibilis, a
protokollverzió emiatt nem változott (marad v1). A módosítást a
Python TCP klienssel (gateway/client.py) manuálisan teszteltem: az
`observe` parancsra adott válasz helyesen tartalmazta mindhárom
szenzor aktuális mérését. A docs/protocol.md dokumentációt is
frissítettük az új válaszmezők leírásával és egy rövid
verziótörténeti bejegyzéssel.

### 17. Baseline vonalkövető kontroller, akadályelkerülés és reset_position (M09 kötelező AI-használat)
A Claude-tól kértem segítséget az M09 mérföldkőhöz: egy
hagyományos, szabály-alapú (nem AI-vezérelt) vonalkövető baseline
kontroller (`controllers/baseline_line_follower.py`) megtervezéséhez
és megírásához - állapotgép (VONALON/KERESES/AKADALY) egy P-
szabályozóval a bal/jobb szenzor intenzitáskülönbségére. Az első
tesztek során kiderült, hogy a rover kerekei nekiütköztek az
akadályoknak fordulás közben, mielőtt a test elfordulhatott volna -
ennek okát (a RoverChassis Scale Z=1.5 túlnyújtása és a kerekek
aránytalan mérete) a Claude segítségével azonosítottuk és
javítottuk (Scale Z 1.0-ra, kerekek arányosítva). Emellett a Claude
megírta a LidarSensor szektoradatainak (`lidar_szektor_min`)
observe-válaszba integrálását az akadályelkerüléshez, és egy új
`reset_position` protokollparancsot (a meglévő
BiztonsagosHibaReset/RoverAzonnaliLeallitasa segédmetódusok
újrahasznosításával), hogy a kísérleti futások azonos
kezdőállapotból induljanak.

Két mérési sorozatot (30-30 futás) végeztünk: az elsőben átlagosan
3.9 akadálykerülést mértünk nagy szórással (0-23), amit egy
oszcilláló akadály-elkerülési viselkedésre gyanakodva hiszterézis
bevezetésével (0.5 m belépési / 0.8 m kilépési küszöb) és a
fordulási szög növelésével (15°→45°) próbáltunk kezelni. A második
mérés (átlag 4.6, szórás 5.0, 0-12 tartomány) azt mutatta, hogy ez
a beavatkozás **nem oldotta meg érdemben** a jelenséget - a nyers
adatokban kétmodális eloszlás maradt (a futások kb. egyharmada
10-12 körüli, ismétlődő akadálytalálkozást mutatott). Ezt a
mérföldkő dokumentációjában (docs/m09-plan.md) őszintén, negatív/
vegyes eredményként rögzítettük, a gyökérok pontos diagnosztizálását
(lépésenkénti naplózás hiányában) jövőbeli munkaként (M10)
azonosítva, nem próbáltuk tovább vakon paraméter-hangolással
"eltüntetni" a jelenséget.

### 18. M10: ütközésdetektálás, lépésnaplózás, vonal-visszakeresés (M10 kötelező AI-használat)
Az M10 mérföldkő elején a Claude-tól kértem, hogy a hivatalos
feladatkiírás alapján állítson össze egy M10 tervet
(`docs/m10-plan.md`), majd a repó tényleges állapotát egyeztetve vele
derült ki két, korábban észrevétlen rés: a `docs/protocol.md` nem
dokumentálta a már M08 óta létező `lidar_szektor_min` mezőt, és a
rendszernek egyáltalán nem volt ütközésdetektálása (az "akadálykerülések
száma" metrika valójában csak az AKADÁLY állapotba lépések számát
mérte, nem a kerülés sikerességét). A Claude ezeket pótolta: `Akadaly`
tag bevezetése (`TrackController.cs`, `TagManager.asset`),
`OnCollisionEnter` kezelő és `collision_occurred`/`collision_count`
mezők (`RoverGatewayServer.cs`, `observe` válasz), dokumentálva
`docs/protocol.md`-ben, kizárólag diagnosztikai célként megjelölve.

Emellett a Claude megírta a lépésenkénti diagnosztikai naplózást
(`LepesNaplozo` osztály a baseline kontrollerben), egy heurisztikus
oszcilláció-kereső elemzőszkriptet (`controllers/analyze_step_log.py`),
és egy új, teszteletlen `VISSZATALALAS` állapotot az akadálykerülés
utáni explicit vonal-visszakereséshez (az elkerülési iránnyal
ellentétes irányba forogva keres, és `KERESES`-re eszkalál, ha nem
talál vonalat). Az állapotgép mind a négy állapotára írt 9 unit tesztet
(`tests/baseline_line_follower_test.py`, stub gateway-kliens, Unity
nélkül futtatható) - mind zöld.

**Emberi ellenőrzés (Unity Play mód):** manuálisan teszteltem az
ütközésdetektálást Play módban - egy mindig aktív teszt-objektumot
(`TesztAkadaly`) ideiglenesen `Akadaly` taggel ellátva, és a rover
pozícióját kézzel ráállítva, az `OnCollisionEnter` helyesen és
ismételten lefutott a Console naplóban. Ezzel megerősítést nyert,
hogy a mechanizmus működik.

A teszt közben egy fontos, nem tervezett módszertani problémát is
feltártunk: ha a rover mélyen belelóg egy akadályba és ott marad, a
fizikai motor minden lépésben újra meghívja az `OnCollisionEnter`-t,
így egyetlen folyamatos ütközés a jelenlegi implementációval több
tucat különálló eseményként számolódik (13-szor nőtt a számláló
néhány másodperc alatt egyetlen beragadás során). Ezt dokumentáltuk a
`docs/m10-plan.md`-ben, mint az éles mérés előtt kötelezően javítandó
hibát - nem hallgattuk el és nem próbáltuk "belesimítani" az
eredménybe.

A `VISSZATALALAS` állapot tényleges Unity Play mód-os viselkedése
még nem lett kipróbálva - ez a következő lépés.

**Utólagos javítás (ugyanaznap):** a fenti, dokumentált többszörös
ütközés-számlálási hibát kijavítottuk. Az első próbálkozás (a
`OnCollisionEnter`/`OnCollisionExit` pár segítségével számolt, hány
akadállyal érintkezik éppen a rover) **nem vált be** - egy
diagnosztikai naplózással feltártuk, hogy a rover több colliderje
(alváz + 4 kerék) egyszerre, mélyen átfedésben egy akadállyal
instabil, oda-vissza ugráló érintkezés-jelzéseket okozott a fizikai
motorban, így a számláló továbbra is hamisan magas maradt. Ehelyett egy egyszerűbb, időalapú "hűtési" (cooldown) mechanizmusra váltottunk
(0.5 másodperc): ez manuálisan tesztelve bevált - egy rögzített
pozícióban a számláló nem nőtt tovább több mint két percig, míg a
korábbi verzióval percenként több tucatszor nőtt volna.

**A `VISSZATALALAS` állapot Unity Play mód-os validálása:** 10
automatizált futást hajtottam végre a baseline kontrollerrel az
eredeti (időzített) szcenárión. 18, teljes 500 lépésig lefutott
"tiszta" futás közül 11-ben aktiválódott a `VISSZATALALAS` állapot,
és mind a 11 esetben sikeresen visszatalált a vonalra, egyetlen
eszkalálás sem történt a tágabb `KERESES` állapotra. A Claude
figyelmeztetett, hogy ez a mintaméret (11 esemény) kicsi az
általános megbízhatóság megállapításához, ezt a korlátot a
`docs/m10-plan.md`-ben is dokumentáltuk.

Eközben egy saját hibámat is érdemes rögzíteni: a tesztelés
felgyorsítása érdekében ideiglenesen "örökké láthatóvá" tettem a
szcenárió akadályait a szcenárió-JSON-ban - ez torzította a mérést
(a rover a pálya körbejárása során ismételten ugyanabba az
akadályba futott, 17-39 ütközés/futás, gyakori pályaelhagyás). A
Claude segített felismerni a torzítás okát és visszaállítani az
eredeti időzítést, ami után a viselkedés visszatért az M09-cel
konzisztens, egészséges mintázathoz.

**Zsákutca-kezelés (ugyanaznap):** a Claude-tól kértem a `docs/m10-plan.md`
5. munkacsomagjának (zsákutca és eltűnő akadály kezelése)
megvalósítását. Egy explicit lépésszámláló bevezetésével (ha a rover
`ZSAKUTCA_AKADALY_MAX_LEPES` lépésig nem tud kikerülni egy akadályt,
a `KERESES` állapotra eszkalál, külön statisztikaként számolva) és
egy hozzá tartozó unit teszttel egészítettük ki a rendszert. Az
eltűnő akadály esetére a Claude azt javasolta, hogy ezt **ne**
próbáljuk explicit módon megkülönböztetni a sikeres kerüléstől
valós időben, mert az privilegizált pozíció-adat használatát
igényelné a vezérlési döntésben - ehelyett dokumentáltuk ezt mint
tudatos tervezési korlátot, ami utólag, diagnosztikai célra a
lépésnaplóból elemezhető.

A manuális szerkesztés (Rider-ben, kézzel másolva/beillesztve) során
két kódszerkesztési hiba is becsúszott: egyszer egy `import`-lista
csere véletlenül szintaktikai hibát okozott, egyszer pedig egy
függvényhívás módosítása közben egy `elif` ág rossz behúzással és
rossz argumentum-sorrenddel csúszott be. Mindkettőt a hibaüzenetek
(`SyntaxError`, `TypeError`) alapján, a kód pontos, aktuális
állapotát megnézve azonosítottuk és javítottuk - egyik esetben sem
próbáltunk vakon, a tényleges fájltartalom ellenőrzése nélkül
módosítani.

**Akadály-időzítés javítása és végleges mérés (ugyanaznap):** a
végleges 30 futásos mérési sorozat közben derült ki egy komoly,
korábban észrevétlen hiba - az akadályok `schedule.appear_at_s`/
`disappear_at_s` időzítése a Play mód *indításához* volt kötve, nem
az egyes futások `reset_position` parancsához. Ez azt jelentette,
hogy az akadályok gyakorlatilag csak egyszer, röviddel a Play mód
elindítása után jelentek meg, utána egy teljes Play munkamenetben
soha többé - így a korábbi mérési sorozatok jelentős része
valójában akadály nélkül futott. A Claude-dal együtt azonosítottuk
a gyökérokot (a `TrackController.Update()` a `Time.timeSinceLevelLoad`
abszolút értékét használta), és bevezettünk egy
`UjrakezdiAkadalyUtemezest()` nyilvános metódust, amit a
`RoverGatewayServer` minden `reset_position` parancsnál meghív.
Eközben egy másik hibát is találtunk és javítottunk: a
`TrackController.FelepitAkadalyokat()` korábban sosem törölte a
korábban létrehozott akadályokat újraépítés előtt, ami Editor-beli
újrafordításoknál duplikálódáshoz és `MissingReferenceException`-höz
vezetett.

Menet közben kiderült egy további, gyakorlati korlát is: a 70x Time
Scale miatt a hálózati parancsok oda-vissza útja alatt is több
szimulált másodperc telik el, így az eredeti, rövid (5-7 másodperces)
időzített akadály-ablakot TCP-n keresztül irányítva gyakorlatilag
lehetetlen eltalálni. Emiatt a végleges méréshez **tudatosan és
dokumentáltan** állandóan láthatóvá tettük az akadályokat (eltérve az
eredeti, tervezett időzített szcenáriótól) - ezt a döntést és a
korlátot a `docs/m10-plan.md`-ben egyértelműen jelöltük, nem
próbáltuk elhallgatni vagy "véletlennek" beállítani.

A végleges mérés (30 futás, mindkét akadály állandóan látható): átlag
2.8 akadálykerülés/futás, 0 zsákutca, de **18/30 futásban
pályaelhagyás** és átlag 20.9 ütközés/futás. A Claude egyértelműen
jelezte, hogy ez nem az M10-es fejlesztések (ütközésdetektálás,
VISSZATALALAS, zsákutca-kezelés) hibája - azok külön-külön, célzott
teszteken igazoltan helyesen működnek -, hanem az M09-ben már ismert
oszcillációs probléma élesebb megjelenése, mert az állandóan jelenlévő
akadály nem ad esélyt a rovernek "megúszni" egy rossz elkerülési
döntést. A gyökérok-javítást nem próbáltuk ebben a mérföldkőben
megoldani, hanem explicit módon M11+ munkaként azonosítottuk.

Ez a szakasz sok manuális Unity/Rider-műveletet igényelt (script-
módosítások, Time Scale állítgatása, JSON-szerkesztés), és menet
közben több félresikerült próbálkozás is volt, mire a Claude
azonosította a tényleges gyökérokot - ezt szándékosan nem
szépítettem el, mert a folyamat maga is tanulság: első ránézésre
"nem működik az akadálykerülés" jelenség mögött végül egy
infrastrukturális (időzítési) hiba állt, nem a vezérlési logika
hibája.

**M10.5 (ugyanaznap, utólagos gyökérok-javítás):** az M09/M10-ben
dokumentált oszcillációs jelenség gyökérokát a Claude az
`analyze_step_log.py` végleges mérési adaton történő lefuttatásával
azonosította: az AKADALY állapot korábban kizárólag fordult, sosem
haladt előre, ezért a rover valódi oldaltávolság-nyerés nélkül látta
"tisztának" a kilátást egy kis elfordulás után. Két javítási
kísérlet is történt, mindkettő őszintén dokumentálva:

1. Első kísérlet (45°-os fordulás + előrehaladás minden lépésben):
   Unity Play módos, videóval dokumentált teszt megmutatta, hogy a
   rover nagy, tág köröket írt le az akadály körül, elhagyva a
   vonalat - a diagnózis helyes volt, a megvalósítás túl durva.
   Elvetve.
2. Finomított javítás (15°-os fordulás + előrehaladás): videóval
   megerősítve, hogy a rover következetesen körbejárja a pályát.
   30 futásos mérés: pályaelhagyás 60%->3.3%.
3. Második finomítási kísérlet (biztonsági távolság küszöb az
   előrehaladáshoz): 30 futásos mérés nem mutatott javulást, sőt
   rontott az eredményen. Elvetve.
4. `AKADALY_KUSZOB_KILEPES_M` paraméterkeresés (0.8 -> 1.5 -> 1.1):
   az 1.1-es érték minden mutatóban a legjobb eredményt adta:
   pályaelhagyás 60%->0%, átlagos ütközésszám 20.9->10.2.

Minden lépésnél a Claude adta a diagnózist és a konkrét kódjavaslatot,
a felhasználó pedig Unity Play módban, kézzel (Rider-ben szerkesztve)
vezette be a saját projektjébe, és videóval/naplóadattal ellenőrizte
minden egyes kísérlet tényleges hatását - beleértve a két elvetett,
negatív eredményű kísérletet is. Részletek: `docs/m10-5-plan.md`.


### 19. M11: naplózási séma, replay, CI és egyparancsos kísérletindítás (M11 kötelező AI-használat)

Az M11 minden munkacsomagjánál a Claude adta a tervet és a
kódjavaslatot, a felhasználó Rider-ben/terminálban vezette be és
Unity Play módban, élesben ellenőrizte:

1. **Egységes naplózási séma** (`common/kiserlet_naplo.py`): a
   vezérlési adatok és a privilegizált diagnosztika szándékos
   szétválasztása két blokkra a Claude javaslata volt, hogy a "ne
   használjon privilegizált Unity-pozíciót" elv a naplóból is
   ellenőrizhető legyen.
2. **Replay-vizualizáció** (`controllers/replay_visualizer.py`):
   első verzióban a `collision_occurred` mezőt használtuk, ami a
   teljes útvonalat "ütközöttnek" jelölte; a `RoverGatewayServer.cs`
   forrásának átnézésével a Claude azonosította, hogy a mező ragadós,
   és a `collision_count` lépésenkénti változására váltottunk.
3. **CI-pipeline** (`.github/workflows/ci.yml`): a Claude írta a
   workflow-t; a `protocol_fuzz_test.py` tudatos kihagyása (élő
   Unity kell hozzá) közös döntés. A PAT `workflow` hatáskörének
   hiányát a felhasználó oldotta meg.
4. **Egyparancsos kísérletindítás** (`controllers/futtat_kiserletet.py`):
   a Claude írta; az éles próbán a felhasználó vette észre, hogy az
   összesítő 30 futást ír 3 helyett - a `--utolso` kapcsoló ennek a
   javítása.

5. **Referenciaepizód és CI-bővítés** (elfogadási feltétel): a Claude
   javasolta, hogy a friss klónból reprodukálható referenciaepizód
   ne élő Unity-futásra, hanem egy commitolt lépésnaplóra épüljön
   (`experiments/referencia_epizod/`), és a metrika-ellenőrzés
   (`scripts/referencia_epizod.py`) a CI-ban is fusson. A CI-t a
   kiírás négy előírt elemére bővítettük (tesztek, sémavalidáció,
   pyflakes, dokumentáció-ellenőrzés). A pyflakes három valódi
   hibát talált (nem használt változó/importok), a
   dokumentáció-ellenőrzés (`scripts/ellenoriz_dokumentaciot.py`)
   pedig helyben zöld volt, CI-ban piros: a dokumentumok
   `.gitignore`-olt naplófájlokra hivatkoztak. A javítás nem lazítás
   volt, hanem `git ls-files` alapú ellenőrzés + a futásidőben
   generált fájlok explicit, kommentált listája - így helyben és
   friss klónban azonos eredményt ad.
6. **Replay videó** (`--video` kapcsoló): a Claude implementálta
   matplotlib `FuncAnimation`-nel, a felhasználó a referenciaepizódon
   generálta és ellenőrizte (`docs/videos/m11-referencia-replay.gif`).
7. **Lefedettségi összefoglaló** (`tests/README.md`): a Claude
   állította össze a 29 teszt táblázatát azzal, hogy melyik teszt
   melyik korábbi hibára regressziós; a felhasználó ellenőrizte az
   állításokat.

8. **Unity Edit/Play Mode tesztek**: a Claude írta a tesztfájlokat és
   az asmdef-eket a repó forrásának átolvasása alapján (publikus API:
   `TavolsagAKozepvonaltol`, `LidarSensor.NyersTavolsagok`,
   `ColorSensor.FeherVonalon`); a felhasználó futtatta a Unity Test
   Runnerben és a Unity-hibaüzenetek alapján közösen javítottuk az
   assembly-beállításokat (egy mappa - egy asmdef; Play Mode-hoz üres
   `includePlatforms`). Kiderült, hogy a repóban a korai mérföldkövek
   óta volt Play Mode teszt (`MovementControllerPlayModeTests.cs`), ami
   a dokumentációból hiányzott. **Az első futtatás egy valódi, M07 óta
   lappangó geometriai hibát talált** (fantom fehér ív a stadion
   belsejében, lásd `docs/m11-plan.md` 3. munkacsomag): a Claude
   azonosította az okot a teszt hibaüzenetéből, javasolta a javítást
   és a regressziós tesztet, a felhasználó Unity-ben ellenőrizte
   (5/5 + 5/5 zöld).

Egy Unity-crash után `Assets/_Recovery/` mappa keletkezett; a Claude
a jelenetfájlok objektumneveinek összevetésével (`grep m_Name`)
igazolta, hogy a mentett `TrackScene.unity` teljes, a recovery csak
duplikált, futásidőben generált akadályokat tartalmazott - törölve.

## Megjegyzések
Az AI (Codex) által generált kódot mindegyik esetben átnéztem és kipróbáltam,
mielőtt bekerült a `src/main.py` fájlba.
