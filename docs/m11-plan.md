# M11 terv: naplózás, replay, automatizált tesztek és CI

## Cél

A projekt átalakítása kutatási demonstrátorból reprodukálható
kísérleti platformmá: egységes naplózás minden kontrollerhez,
replay-eszköz, kiegészítő tesztek, CI-pipeline és egyparancsos
kísérletindítás.

## Állapot: LEZÁRVA (`m11` tag)

Mind a hat munkacsomag kész. A kiírás (Table 19) elfogadási feltételei:
- hibák logból visszakövethetők - igen (a "ragadós" `collision_occurred`
  és a fantom-ív hiba is naplóból/tesztből került elő);
- referenciaepizód friss klónból reprodukálható - igen
  (`scripts/referencia_epizod.py`, Unity nélkül, CI-ban is fut);
- CI zöld - igen (tesztek + sémavalidáció + black formázás-ellenőrzés + pyflakes + dokumentáció-ellenőrzés).

GitHub-bizonyítékok: `m11` tag, `REPRODUCIBILITY.md` (5b. fejezet + M11
sor), CI badge a README-ben, replay videó
(`docs/videos/m11-referencia-replay.gif`), `tests/README.md`
lefedettségi összefoglaló.

Az M11 során talált és javított örökölt hibák: (1) fantom fehér ív a
pálya-geometriában (M07 óta, Unity Edit Mode teszt találta), (2) az
összesítő mindig 30 futást nézett az indított N helyett, (3) pyflakes:
nem használt változó/importok, (4) dokumentumok nem verziókövetett
naplófájlokra hivatkoztak (CI doc-check találta).

## 1. munkacsomag: egységes naplózási séma (kész)

Létrehoztunk egy új, önálló Python-csomagot (`common/kiserlet_naplo.py`),
amit minden jelenlegi és jövőbeli kontrollernek (hagyományos baseline,
agent-alapú, tanult policy) egységesen kell használnia. A modul két
osztályt ad: `KiserletMetaadat` (run-szintű: `controller`, `backend`,
`seed`) és `KiserletNaplozo` (lépésenkénti JSONL-naplózó).

A naplózott mezők szándékosan két csoportra oszlanak:
1. Vezérlési szempontból releváns adatok (`szenzorok`, `parancsok`,
   `allapot_elotte`/`allapot_utana`) - ezeket a kontroller ténylegesen
   felhasználhatja döntéshozatalhoz.
2. Privilegizált diagnosztikai adatok (`privilegizalt_diagnosztika`:
   `position`, `collision_occurred`, `collision_count`) - ezek
   kizárólag utólagos elemzésre szolgálnak, külön blokkban, hogy
   egyértelműen elkülönüljenek a vezérlési adatoktól.

A `controllers/baseline_line_follower.py`-t átírtuk, hogy a régi,
beépített `LepesNaplozo` osztály helyett ezt az új, közös modult
használja. A naplófájl neve szándékosan más (`logs/kiserlet_naplo.jsonl`),
mint a korábbi, M10-es `logs/m10_lepes_naplo.jsonl`, hogy a régi és az
új formátum egyértelműen elkülönüljön.

A bekötést Unity Play módban, élesben is ellenőriztük: a naplósor
helyesen tartalmazza az összes tervezett mezőt, a teljes tesztkészlet
(10 teszt) zöld maradt.

## 2. munkacsomag: replay-vizualizáció (kész)

Létrehoztunk egy `controllers/replay_visualizer.py` szkriptet, ami a
`logs/kiserlet_naplo.jsonl` alapján egy adott futás pálya-nyomvonalát
rajzolja ki (matplotlib), állapot szerint színezve, az ütközéseket
külön jelölve. Ez nem egy "valódi" replay (nem küldi újra a
parancsokat Unity-nek), hanem egy egyszerű, utólagos vizualizáció -
ez teljesíti a kiírás "legalább vizualizálja" minimumkövetelményét.

A fejlesztés közben egy valódi, apró hibát találtunk és javítottunk:
első próbálkozásra a `privilegizalt_diagnosztika.collision_occurred`
mezőt használtuk az ütközések jelölésére, ami szinte a teljes
útvonalat "ütközöttnek" jelölte. A forráskód vizsgálata (
`RoverGatewayServer.cs`, `utkozesTortentAzUtolsoResetOta` változó)
megerősítette: ez a mező "ragadós" - egyszer igazzá válva a teljes
futás hátralévő részére igaz marad, nem csak az adott lépésre. A
javítás a `collision_count` mező lépésenkénti **változásának**
figyelését jelentette, ami helyesen csak az akadályok tényleges
helyénél jelölt ütközést.

Egy érdekes, a replay-eszköz által feltárt megfigyelés: egy
konkrét futásban (`702a82a6`) történt néhány ütközés úgy, hogy a
rover a teljes futás alatt VONALON állapotban maradt, sosem lépett
AKADALY állapotba - ez arra utalhat, hogy a rover néha súrolja az
akadályt anélkül, hogy a LiDAR időben észlelné. Ez a fajta megfigyelés
pontosan a replay-eszköz céljának megfelelő, további vizsgálatra
érdemes jelenség (M11+ munkára utalva).

### 2b. Animált replay (videó)

A `replay_visualizer.py` `--video` kapcsolója animált változatot készít:
a nyomvonal lépésről lépésre épül fel, a rover aktuális pozíciója és
állapota, valamint az addigi ütközések száma képkockánként frissül.
GIF-be ment (Pillow, ffmpeg nélkül), `.mp4` kiterjesztésnél ffmpeg-et
használ, ha elérhető. A referenciaepizód videója:
`docs/videos/m11-referencia-replay.gif` (500 lépés, 251 képkocka, 20 fps).

```bash
python3 controllers/replay_visualizer.py \
  --naplo-fajl experiments/referencia_epizod/referencia_epizod.jsonl \
  --run-id 97994315 --video docs/videos/m11-referencia-replay.gif
```

## 3. munkacsomag: Unity Edit/Play Mode és Python tesztek (kész)

Python-oldal: 23 Unity-t nem igénylő teszt + 6 fuzz teszt + a
referenciaepizód integrációs ellenőrzése (részletek: `tests/README.md`).

Unity-oldal (`unity/Assets/Tests/`):
- **Edit Mode** (`unity/Assets/Tests/EditMode/TrackControllerGeometriaTeszt.cs`, 5 teszt): a
  `TrackController.TavolsagAKozepvonaltol` geometriája jelenet nélkül -
  egyenes szakasz, ív, pálya közepe, vonalszélesség-küszöb, fantom-ív.
- **Play Mode** (`unity/Assets/Tests/PlayMode/TrackSceneTeszt.cs`, 3 teszt + a korai
  mérföldkövekből örökölt `MovementControllerPlayModeTests.cs` 2 tesztje):
  a `TrackScene` betöltődik a kötelező komponensekkel; a Lidar a beállított
  sugárszámmal, hatótávon belüli értékekkel mér; a középső színszenzor
  ítélete (fehér/nem fehér) megegyezik a pálya-geometria ítéletével.
  A jelenetet `EditorSceneManager.LoadSceneInPlayMode` tölti be, így nem
  kell a Build Settings-be venni.

Eredmény: 5/5 Edit Mode és 5/5 Play Mode zöld
(`docs/screenshots/m11-unity-tests-editmode.png`,
`docs/screenshots/m11-unity-tests-playmode.png`).

**A tesztek első futtatása valódi hibát talált.** A `PalyaKozepen` teszt a
(0, 0) pontra 4 m helyett 2 m távolságot kapott: a `TavolsagIvtol` a
teljes körhöz mérte a távolságot, nem a félkörívhez. Következmény: a
stadion belsejében egy "fantom" fehér ív futott (a felső kör alsó és az
alsó kör felső fele, pl. a (0, ±2) pontokon 0 távolsággal), ahol a
`ColorSensor` tévesen teljes fehéret mért volna - egy KERESES közben
befelé sodródó rover nem létező vonalra találhatott. A hiba M07 óta
lappangott. Javítás: a félkörív csak a saját oldalán érvényes (irány
paraméter), a másik oldalon a végpontjait az egyenes szakaszok fedik.
Regressziós teszt: `FantomIv_AStadionBelsejeben_NincsVonalon`.

Tanulságok:
- egy mappában csak egy `.asmdef` lehet;
- `"includePlatforms": ["Editor"]` Edit Mode-assemblyvé teszi a tesztet -
  Play Mode-hoz üres platformlista kell, az Editor-API `#if UNITY_EDITOR`
  mögé;
- a `[ExecuteAlways]` TrackController Edit módban is legenerálja az
  akadályokat, és ezek a jelenetfájlba kerülhetnek mentéskor - commit
  előtt `git diff` a `TrackScene.unity`-n; M12+ apró javítás:
  `HideFlags.DontSave` az Edit módban generált objektumokra.

## 4. munkacsomag: CI-pipeline (kész)

Létrehoztunk egy GitHub Actions workflow-t (`.github/workflows/ci.yml`),
ami minden `main`-re történő push-nál és pull requestnél automatikusan
lefuttatja a Python-tesztkészletet: `baseline_line_follower_test.py`,
`kiserlet_naplo_test.py`, `replay_visualizer_test.py`,
`scenario_seed_test.py`. A `protocol_fuzz_test.py`-t tudatosan
kihagytuk a CI-ból, mivel élő Unity-kapcsolatot igényel, ami a
GitHub Actions futtatókörnyezetben nem elérhető (lásd
`REPRODUCIBILITY.md`, Ismert korlátok).

Az első két futtatás mindkétszer sikeresen, kb. 32-38 másodperc
alatt lefutott. A README tetejére egy CI badge-et is felvettünk,
ami a build aktuális állapotát mutatja.

A workflow-fájl feltöltésekor egy jogosultsági korlátba ütköztünk: a
használt Personal Access Token alapból nem rendelkezett `workflow`
hatáskörrel, ami szükséges a `.github/workflows/` alatti fájlok
push-olásához - ezt a token jogosultságainak frissítésével oldottuk
meg.

## 5. munkacsomag: egyparancsos kísérletindítás (kész)

Létrehoztuk a `controllers/futtat_kiserletet.py` szkriptet, ami egyetlen
paranccsal lefuttat N darab baseline-futást egymás után, majd a végén
automatikusan meghívja a `controllers/summarize_runs.py` összesítőt:

```bash
python3 controllers/futtat_kiserletet.py --futasok-szama 30
```

Az első éles, 3 futásos próbán a láncolt indítás hibátlanul működött,
de az összesítő "30 futás"-t írt ki, mert a `summarize_runs.py`
mindig a napló utolsó 30 sorát nézte, függetlenül attól, hány futás
indult most. Javítás: a `summarize_runs.py` kapott egy `--utolso N`
kapcsolót, és a `futtat_kiserletet.py` ezt a ténylegesen elindított
futások számával hívja meg - így az összesítés pontosan az új
futásokra vonatkozik (2 futásos ellenőrzés: `Osszegzes (2 futas)`).

Ismert korlátok:
- a szkript jelenleg csak a `baseline_line_follower.py`-t tudja
  indítani; az agent-alapú és tanult kontrollerekhez (M12+) egy
  `--controller` kapcsolóval kell bővíteni;
- `--futasok-szama 1` esetén a `statistics.stdev` hibát dob (egy
  elemből nincs szórás) - mérésekhez ez nem releváns, de érdemes
  kezelni;
- a run-szintű napló neve történeti okból `logs/m09_runs.jsonl`
  maradt, bár M10 óta minden futás oda íródik.

## Hátralévő munkacsomagok
Nincs. Mind a hat munkacsomag kész; a lezárás (tag, README, CITATION,
Milestone, retrospektív Issue) az M11 zárásakor történik.

Nyitott, M12+ pontok: valódi parancs-visszajátszás Unity-ben; Unity-tesztek
futtatása CI-ban (Unity licenc/GameCI); `HideFlags.DontSave` az
`ExecuteAlways` által Edit módban generált akadályokra; `--controller`
kapcsoló a `futtat_kiserletet.py`-ban.