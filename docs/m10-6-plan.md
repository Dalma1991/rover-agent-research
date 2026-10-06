# M10.6 (nem hivatalos): az akadálykerülés újramérése és javítása

**Állapot:** lezárva, de az **M10 elfogadási feltétele továbbra sem teljesül** —
lásd az értékelést a dokumentum végén.

Az M10.5-höz hasonlóan ez sem hivatalos mérföldkő, hanem utólagos javítás. A
hivatalos számozás nem csúszik: a következő mérföldkő az M13.

## Miért volt szükség rá

Az M11-ben a Unity Edit Mode tesztek egy M07 óta lappangó geometriai hibát
találtak: a `TrackController.TavolsagIvtol` a teljes körhöz mérte a
távolságot, nem a félkörívhez, ezért a stadion **belsejében egy nem létező,
„fantom" fehér ív** futott végig. A hibát az M11-ben javítottuk, de az addigi
mérések ezzel a hibával készültek.

A javított geometriával újraszámolva az M10-es végleges 30 futás
(`logs/m10_vegleges_30_futas_lepesnaplo.jsonl`, `controllers/kor_metrika.py`):

| Metrika | Érték |
|---|---|
| Valódi vonalon töltött lépések | **26.8%** |
| Teljes kört tett meg | 0/30 |
| Kör-arány | átlag 0.079 |

Vagyis a rover az idő háromnegyedében nem a valódi vonalon volt, mégis fehéret
látott: **a fantom ívet követte**. Ez nem elméleti kockázat volt, hanem a
mérések érvényességét érintő hiba — az M10.5-ös „pályaelhagyás 60% → 0%"
eredmény részben azért született, mert a pályát elhagyó rover is talált egy
„vonalat", amit követhetett.

Ezen felül a task success (teljesített kör) korábban **matematikailag
kizárt** volt: a pálya kerülete 49.1 m, egy lépés 0.08 m, tehát egy kör
legalább 614 lépés — a mérések viszont 500 lépéses kerettel futottak.

## Diagnózis: három egymásra épülő hiba

A javított geometriával, akadályokkal futtatott mérés lépésnaplójából
(`VONALON → AKADALY → VISSZATALALAS → KERESES` átmenetek és a privilegizált
pozíció összevetésével) három hiba derült ki:

1. **Az AKADALY túl korán lépett ki.** A kilépési feltétel csak az *elülső*
   lidar-szektorokat (2, 3) nézte. Amikor a rover 45 fokot fordult, elöl
   tisztának látta az utat, pedig az akadály még *mellette* volt (a 0–1.
   szektorban 0.7 m).
2. **A VISSZATALALAS visszafordult az akadályba.** A kilépés után azonnal
   elkezdett visszafordulni a vonal felé — pontosan oda, ahol az akadály volt.
   A napló szerint 8 lépéssel később a lidar újra 0.3 m-t mutatott elöl, és
   sorozatos ütközések következtek.
3. **A KERESES helyben forgott.** Csak `turn` parancsokat adott, `move`
   nélkül. Akadálykerülés után a rover fél méterre is kerülhet a vonaltól —
   helyben forgással egy ilyen távoli vonal **matematikailag
   megtalálhatatlan**, mert a szenzorok a rover alatt vannak.

Egy negyedik hiba a javítás közbeni mérésekből jött elő:

4. **ERROR-állapotban ragadás.** A `futtat()` a futás elején csak
   `reset_position`-t küldött, ami a protokoll szerint **csak IDLE-ben**
   működik. Ha egy futás ERROR-ral végződött, a következő futás nem tudott
   resetelni: a rover a pályán kívül ragadt, minden mozgásparancsot
   elutasított, és négy egymást követő futás adott azonos, értelmetlen
   eredményt (121 lépés, 0.0 m megtett út). Ez a hiba M09 óta benne volt.

## Javítások

| # | Javítás | Hol |
|---|---|---|
| 1 | Az AKADALY új, „elhaladási" fázisa: ha elöl már szabad, de az akadály még az elkerülés oldalán van, a rover **nem fordul tovább**, csak egyenesen elhalad, amíg az akadály mögé nem kerül (`akadaly_oldalt()`, `AKADALY_KUSZOB_OLDAL_M = 1.0`). A zsákutca-számláló csak az elöl zárt lépéseket számolja | `baseline_line_follower.py` |
| 2 | A VISSZATALALAS visszatér az AKADALY állapotba, ha újra akadály kerül elé | ugyanott |
| 3 | A KERESES `turn` **és** `move` parancsot ad, így körívet ír le helyben forgás helyett; ha akadály kerül elé, az AKADALY-ba vált | ugyanott |
| 4 | A futás előtt `get_status` → ha ERROR, akkor `reset_error` + `stop` + `reset_position` | `futtat()` |

## Elvetett javítás 1.: táguló spirál

A sikertelen futások mind a KERESES-ben, **1.4–1.5 m-re a vonaltól** értek
véget — épp a fix körív 2.3 m-es átmérőjén kívül. Ebből az a hipotézis
adódott, hogy egy táguló spirál (8 fok → 2 fok, 120 lépés) megtalálná a
távolabbi vonalat is. A mérés ezt **megcáfolta**: a rover nem esett ki
(pályaelhagyás 0/5), de a 9.6 m-nyi kanyargás közben eltávolodott a vonaltól
és folyamatosan ütközött — 163 ütközés futásonként, és a lépések mindössze
9%-ában volt a valódi vonalon (a szűk körívvel 30%). A spirál ezért ki van
kapcsolva (`KERESES_SPIRAL_CSOKKENES = 0.0`), a paraméter és a mérés
tanulsága viszont a kódban maradt.

## Elvetett javítás 2.: akadálykontúr-követés (bug-algoritmus)

**Mérés dátuma:** 2026-10-06. Kiinduló hipotézis: a rover azért veszíti el a
vonalat, mert az akadály mellett elhaladva csak egyenesen megy, és nem tudja,
hol a vonal. A szakirodalomból ismert megoldás a kontúrkövetés: P-szabályozó
tartson állandó oldaltávolságot (0.6 m) az akadálytól, a lidar oldalsó
szektoraira — ugyanaz az elv, mint a vonalkövetés a színszenzorokra. Az
érvelés elegáns volt: mivel **az akadály a vonalon ül**, a kontúrja mentén
haladva a geometria magától visszavisz a vonalhoz.

Ehhez társult egy második, önmagában helyes javítás is: a
`VISSZATALALAS_MAX_LEPES` 15-ről 80-ra emelése. Az 5 fokos lépésenkénti
fordulat 0.92 m sugarú kört ír le, ami 1.84 m-en belül bármilyen vonalat
metsz — de csak ha a rover befejezi a kört; 15 lépés mindössze 75 fokot
fordult, a teljes körhöz 72 lépés kellene.

A mérés (5 futás, azonos Unity-példányon, közvetlenül egy M10.6-os
kontrollméréssel összevetve) **egyértelműen megcáfolta**:

| Metrika | M10.6 (kontroll, 5 futás) | Kontúrkövetés (5 futás) |
|---|---|---|
| Ütközés / futás | 67.6 | **349.6** |
| Task success | 1/5 | 0/5 |
| Hatékonyság | 0.427 | 0.117 |
| Zsákutca-eszkaláció | 0.0 | **11.4** |
| Akadálykerülés / futás | 3.6 | 12.2 |

A 11.4-es zsákutca-szám és a 12.2 akadálykerülés árulja el az okot: a rover
**körbe-körbe kering az akadály körül**. A P-szabályozó pontosan azt teszi,
amire tervezték — 0.6 m-en tartja az akadályt —, csakhogy így soha nem engedi
el: a kilépési feltétel (az akadály eltűnik az oldalsó szektorokból) sosem
teljesül, mert a szabályozó aktívan a látómezőben tartja. Önfenntartó hurok.

Ez a wall-following klasszikus hibája: hiányzik a **leave condition**. A
teljes bug-algoritmusban a rover akkor hagyja el a kontúrt, amikor a
haladási iránya újra az eredeti célirányba fordul — ehhez viszont tudnia
kellene, merre volt a vonal, vagyis **odometriára** lenne szükség (a rover
saját, kiadott parancsaiból integrált elmozdulás; ez nem privilegizált adat,
egy valódi roveren a kerék-enkóderek adnák). Ez már egy újabb, nagyobb
fejlesztési kör, ezért nem valósult meg.

A kontúrkövetés és a megemelt VISSZATALALAS-keret ezért **nem került be** a
kódba; a baseline az M10.6-os konfigurációban maradt.

### Módszertani tanulság

Két, elvileg helyes és a szakirodalomból vett javítás is rontott, miközben a
mögöttük álló diagnózis mindkét esetben korrekt volt (a spirálnál a mért
1.4–1.5 m-es távolság a körív átmérőjén kívül; a kontúrkövetésnél az, hogy a
rover nem tudja, hol a vonal). Egy kézzel hangolt, emlékezet nélküli
állapotgépen a lokálisan ésszerű szabályok globálisan rossz viselkedést
adnak. Ez teszi érdekessé az M13-as összehasonlítást: ha egy agent vagy egy
tanult policy ugyanezzel a szenzorkészlettel jobban boldogul, az önmagában
eredmény — és most már van hozzá mért, dokumentált alapvonal.

## Végleges mérés (30 futás, 1500 lépés, `stadium-train-baseline-always-visible`)

Futásonkénti metrikák: `docs/m10-6-meres.json`. Reprezentatív (medián)
futás teljes nyomvonala: `experiments/m10_6_referencia_futas.jsonl`.
A teljes, 49 MB-os lépésnapló nem verziókövetett.

| Metrika | M10 (fantom ívvel, 500 lépés) | M10.6 (javított, 1500 lépés) |
|---|---|---|
| **Task success (teljes kör)** | 0/30 | **9/30 (30%)** |
| Kör-arány | átlag 0.079 | átlag 0.690 (max 1.96) |
| Hatékonyság | 0.348 | 0.453 |
| Valódi vonalon töltött lépések | 26.8% | 29.9% |
| Pályaelhagyás | — | 20/30 |
| Ütközés / futás | 20.8 | 77.4 |
| **Ütközésmentes futás** | 0/30 | **0/30** |

Kontrollmérés **akadályok nélkül** (időzített szcenárió, 5 futás): task
success **5/5**, kör-arány 1.62, hatékonyság **0.971**, ütközés 0. Vagyis a
vonalkövetés maga (M09) a javított geometriával kifogástalan — a probléma
kizárólag az akadálykerüléshez kötődik.

## Értékelés: az M10 elfogadási feltétele NEM teljesül

A kiírás M10-es elfogadási feltétele: *„a rover ütközés nélkül visszatér a
vonalra a szcenáriók többségében"*. A mért érték **0/30** — egyetlen
ütközésmentes futás sem volt. A kapu tehát **nyitva marad**, és ezt sem a
README, sem a mérföldkő-dokumentáció nem állítja másként.

Ami viszont javult és igazolható:

- a task success 0-ról 30%-ra nőtt, és a rover ténylegesen megkerüli az
  akadályokat (nem egy fantom vonalat követ);
- a mérés maga érvényessé vált: a fantom ív megszűnt, a keret elegendő egy
  teljes körhöz, és a task success közvetlenül mérve van;
- négy valódi hiba javítva, köztük egy M09 óta lappangó (ERROR-reset).

Ami nyitva marad (M13+):

- **Az ütközésmentesség.** A rover súrolva kerüli meg az akadályokat. A
  hangolást négy iteráció után abbahagytuk: az utolsó kettő nem hozott
  javulást, és a további paraméterezés a train-szcenárióra való túlillesztés
  felé vinne — ami épp az a módszertani hiba, amit a `docs/scenario-schema.md`
  train/test szakasza tárgyal.
- **A bimodális viselkedés.** Az ütközésszám szórása 57.8 (3 és 238 között):
  egyes futások simán mennek, mások beragadnak egy akadály mellé. A
  gyökérokot nem tártuk fel.
- **Odometria-alapú visszatalálás.** A két megcáfolt javítási kísérlet közös
  tanulsága, hogy a rovernek emlékeznie kellene arra, merre hagyta el a
  vonalat. A kiadott `turn`/`move` parancsokból integrált elmozdulás-becslés
  (nem privilegizált adat) ezt megadná, és a kontúrkövetésnek is megadná a
  hiányzó leave conditiont.
- A baseline egy egyszerű, kézzel hangolt állapotgép. Az M13+ agent-alapú és
  tanult kontrollerek éppen ezen a ponton mérhetők össze vele: a
  `controllers/kor_metrika.py` és a `--controller` kapcsoló ehhez már készen
  áll.
