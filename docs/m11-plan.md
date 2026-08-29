# M11 terv: az M09/M10-ben dokumentált oszcillációs jelenség gyökérok-vizsgálata

## Cél

Az M09 baseline mérésekor, majd az M10 végleges stresszteszttel
megerősítve dokumentált, kétmodális/oszcillációs jelenség
gyökérokának feltárása és - amennyire lehetséges egy egyetlen
napos munkamenetben - érdemi javítása, a lépésenkénti diagnosztikai
naplózásra (M10) és az `analyze_step_log.py` eszközre építve.

## Kiindulási állapot

Az M10 végleges, 30 futásos stressztesztje (lásd `docs/m10-plan.md`,
6. fejezet) 18/30 pályaelhagyást és átlagosan 20.9 ütközést/futás
mutatott, ami megerősítette (nem okozta) az M09-ben már dokumentált
oszcillációs problémát. A gyökérok ekkor még nyitott kérdés volt,
M11+ munkára utalva.

## 1. munkacsomag: gyökérok azonosítása (kész)

Az `analyze_step_log.py`-t először futtattuk le éles, végleges
mérési adaton (`logs/m10_vegleges_30_futas_lepesnaplo.jsonl`).
Az eredmény: 12/30 futásban volt legalább egy "gyanús" (0.3 m-en
belül helyben ismétlődő) AKADÁLY-belépés, összesen 25 gyanús pár,
szinte kivétel nélkül egyetlen, szűk térbeli régióra (x≈4.52-4.54,
z≈3.29-3.32) koncentrálódva.

Egy konkrét futás (`daa2a403...`) lépésenkénti vizsgálata feltárta a
pontos mintázatot:VONALON -> AKADALY (1-2 lepes) -> VISSZATALALAS (~9-11 lepes)
-> VONALON (1 lepes) -> AKADALY (ujra ugyanaz) -> ...

A forráskód (`controllers/baseline_line_follower.py`,
`egy_lepes_akadaly()`) megerősítette a mechanizmust: az AKADÁLY
állapot **kizárólag fordult**, sosem haladt előre. Emiatt egy kis
elfordulás után a LiDAR elülső szektora "tisztának" látta a
kilátást (a rover még mindig közvetlenül az akadály mellett állt),
majd a VISSZATALALAS visszafordulása - mivel nem történt tényleges
oldaltávolság-nyerés - egyenesen visszavitte az akadályhoz.

**Ez egy konkrét, forráskód-szinten lokalizált hiba volt, nem egy
megfoghatatlan jelenség.**

## 2. munkacsomag: első javítási kísérlet - túllövés (elvetve)

Első próbálkozás: `move` parancs hozzáadása az `egy_lepes_akadaly()`-
hoz a `turn` után, változatlan (45°) fordulási szöggel. Unity Play
módos, videóval dokumentált teszt: a rover **nagy, tág köröket**
írt le az akadály körül, elhagyva a vonalat, és útközben több
akadálynak is nekiütközött. A diagnózis (elő kell haladni, nem csak
fordulni) helyesnek bizonyult, de a megvalósítás túl durva volt:
több egymást követő 45°-os fordulat, mindegyik előrehaladással
kombinálva, összeadódó, nagy szögű elfordulást (akár egy teljes kör
jelentős részét) eredményezte.

## 3. munkacsomag: finomított javítás (kész, jelentős javulással)

`AKADALY_FORDULAT_FOK` csökkentve 45°-ról **15°-ra**, a `move`
paranccsal kiegészítve megtartva. Több Unity Play módos, videóval
megerősített teszt (Time Scale 5, majd 1) igazolta, hogy a rover
ezzel a beállítással **ténylegesen, következetesen körbejárja a
pályát** akadálytalálkozás után is.

### Végleges 30 futásos összehasonlító mérés

| Mutató | M10 (javítás előtt) | M11 (javítás után) |
| --- | --- | --- |
| Pályaelhagyás | 18/30 (60%) | **1/30 (3.3%)** |
| Akadálykerülés/futás, átlag | 2.8 | 2.5 |
| Ütközés/futás, átlag | 20.9 | 21.3 |
| Ütközött futások | 30/30 | 30/30 |

A pályaelhagyás drasztikus (60%→3.3%) csökkenése egyértelműen
igazolja, hogy a gyökérok-diagnózis és a javítás iránya helyes volt:
a rover most már majdnem minden esetben sikeresen befejezi a kört.

## Nyitva maradó, őszintén dokumentált kérdés

Az **ütközésszám nem csökkent** (sőt, van szórásban kiugró érték,
pl. egy futásnál 13 akadálykerülés/99 ütközés). Ez arra utal, hogy
az oszcillációs mintázat **csökkent formában, de nem szűnt meg
teljesen**: a rover néhány futásnál még mindig sokat "araszol" egy
adott akadály mellett, mielőtt sikerülne továbbjutnia - csak ez már
nem vezet pályaelhagyáshoz, mert a `ZSAKUTCA_AKADALY_MAX_LEPES`
korlát és a most már ténylegesen előrehaladó AKADALY állapot együtt
elegendőek ahhoz, hogy végül kikerüljön a helyzetből.

**Ezt nem tekintjük megoldottnak, csak jelentősen enyhítettnek.** A
0.5 mp-es ütközés-cooldown (M10) és a jelenlegi elkerülési heurisztika
finomhangolása (pl. a `move` lépéshossz vagy a `AKADALY_FORDULAT_FOK`
további optimalizálása, esetleg a fordulás és haladás explicit
szétválasztása két fázisra) M12+ munkaként azonosítva.

## Kódmódosítás

`controllers/baseline_line_follower.py`, `egy_lepes_akadaly()`:
`AKADALY_FORDULAT_FOK = 45.0` -> `15.0`, és a fordulás után egy
`move` parancs hozzáadva, ugyanazokkal a lépésparaméterekkel
(`MOVE_LEPES_M`, `MOVE_SEBESSEG`), mint amiket a VONALON és a
VISSZATALALAS állapotok is használnak.

## 4. munkacsomag: második finomítási kísérlet - biztonsági távolság (elvetve)

Feltételezés: az ütközések egy része onnan ered, hogy az AKADALY
állapot **akkor is** előre halad, amikor a rover **még nagyon közel**
van az akadályhoz (esetleg már érintkezésben) - ez fizikailag
nekicsúsztathatja, mielőtt elég elfordult volna. Javasolt javítás:
egy `AKADALY_BIZTONSAGOS_MOZGAS_M = 0.3` küszöb bevezetése, ami alatt
a rover csak fordul, előrehaladás nélkül (mint az eredeti, M09-es
viselkedés), és csak e küszöb felett halad is előre.

**30 futásos összehasonlító mérés (ugyanazon a szcenárión):**

| Mutató | 3. munkacsomag (csak fordulás+haladás) | 4. munkacsomag (+ biztonsági távolság) |
| --- | --- | --- |
| Pályaelhagyás | 1/30 | 3/30 |
| Ütközés/futás, átlag | 21.3 | 22.6 |
| Ütközés/futás, max | 99 | 139 |

Az eredmény **nem mutatott javulást** - sőt, minden mutatóban kissé
rosszabb lett, beleértve egy jelentősen megnövekedett maximális
ütközésszámot (139). A hipotézis (a közeli előrehaladás okozza az
ütközések egy részét) ezzel a konkrét megvalósítással nem nyert
megerősítést; lehetséges, hogy a küszöbérték rosszul volt megválasztva,
vagy hogy a feltételes mozgás megszakítása más módon zavarta meg az
elkerülési dinamikát. **A módosítást elvetettük**, és visszaálltunk a
3. munkacsomag változatlan, feltétel nélküli előrehaladást használó
verziójára, ami a nap folyamán a legjobb mért eredményt adta.

Ezt a negatív eredményt tudatosan dokumentáljuk: nem minden
plauzibilis javítási hipotézis igazolódik be, és ennek nyílt jelzése
ugyanolyan értékes, mint a sikeres javításoké.