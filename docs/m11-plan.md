# M11 terv: naplózás, replay, automatizált tesztek és CI

## Cél

A projekt átalakítása kutatási demonstrátorból reprodukálható
kísérleti platformmá: egységes naplózás minden kontrollerhez,
replay-eszköz, kiegészítő tesztek, CI-pipeline és egyparancsos
kísérletindítás.

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

## Hátralévő munkacsomagok
3. Unity Edit/Play Mode és Python unit/integration tesztek kiegészítése
   (Python-oldal kész, Unity-oldal még hátravan - lásd 3. munkacsomag).
4. CI-pipeline (GitHub Actions): Python tesztek, formázás, sémavalidáció,
   dokumentáció-ellenőrzés.
5. Egyparancsos kísérletindítás és eredmény-összesítés.
6. `REPRODUCIBILITY.md` kiegészítése M07-M10.5-ig (jelenleg csak M06-ig
   részletes).