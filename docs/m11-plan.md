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

## Hátralévő munkacsomagok

2. Replay-eszköz - egy epizód visszajátszása/vizualizálása a logból.
3. Unity Edit/Play Mode és Python unit/integration tesztek kiegészítése.
4. CI-pipeline (GitHub Actions): Python tesztek, formázás, sémavalidáció,
   dokumentáció-ellenőrzés.
5. Egyparancsos kísérletindítás és eredmény-összesítés.
6. `REPRODUCIBILITY.md` kiegészítése M07-M10.5-ig (jelenleg csak M06-ig
   részletes).