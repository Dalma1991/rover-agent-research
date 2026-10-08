# M09 terv: hagyományos (AI nélküli) vonalkövető baseline

## Cél

Egy klasszikus, szabály-alapú (nem tanuló, nem AI-vezérelt)
vonalkövető kontroller megvalósítása és mérése, amely kizárólag a
három vonalérzékelő szenzor (`sensor_left`, `sensor_center`,
`sensor_right`) adataira támaszkodik — nem használja a `position`/
`speed` privilegizált szimulátor-mezőket. Ez szolgál majd
összehasonlítási alapként (baseline) a jövőbeli, tanuló-alapú
kontrollerekhez.

## Architektúra

- **Nyelv:** Python, a meglévő `gateway/client.py` TCP-kliens
  kódjára/mintájára építve.
- **Bemenet:** kizárólag az `observe` parancs `sensor_mode`,
  `sensor_left`, `sensor_center`, `sensor_right` mezői.
- **Kimenet:** `move` és `turn` parancsok a `gateway/client.py`-hoz
  hasonló TCP protokollon keresztül.

## Állapotgép
VONALON --vonalvesztés--> KERESÉS
KERESÉS --vonal megtalálva--> VONALON

### VONALON állapot
A hibajelet a bal és jobb szenzor `intensity` értékének
különbségéből számoljuk (`hiba = intensity_jobb - intensity_bal`).
Egy arányos (P) szabályozó ez alapján dönt a korrekció irányáról és
mértékéről: kis `turn` parancsokat ad ki, amelyek szöge arányos a
hibajel nagyságával (küszöbölt minimum/maximum korrekciós szöggel,
hogy elkerüljük a túlszabályozást). A `sensor_center` elsősorban a
"még a vonalon vagyunk-e" ellenőrzésre szolgál.

### KERESÉS állapot
Akkor lép életbe, ha mindhárom szenzor `white: false`-ot jelez
(elvesztettük a vonalat). Dokumentált keresési minta: lassú,
mindig ugyanabba az irányba történő forgás (pl. az utolsó ismert
hibajel előjele szerint), amíg valamelyik szenzor újra `white:
true`-t nem jelez, ekkor visszavált VONALON állapotba.

### Váltási feltételek (küszöbök)
A pontos numerikus küszöböket (pl. hány egymást követő `observe`
ciklus szükséges a "vonalvesztés" megállapításához) a fejlesztés
során, kézi teszteléssel hangoljuk be, és itt dokumentáljuk, amint
lefixálódtak.

## Mérési módszertan

**Metrikák futásonként:**
- köridő (kiadott parancsok száma és/vagy szimulált idő a pálya
  egy körének teljesítéséhez)
- vonalvesztések száma (hányszor lépett KERESÉS állapotba)
- pályaelhagyás (bool: elhagyta-e a rover a pálya megengedett
  sávját)
- kiadott parancsok száma összesen

**Protokoll:**
- Minimum 30 futás, rögzített pálya-seeddel (a `TrackController`
  jelenlegi `stadium-train-baseline` szcenáriója vagy hasonló,
  reprodukálható beállítás).
- Minden futás eredménye egy sorban kerül naplózásra (`.jsonl`
  vagy `.csv` formátumban), hogy utólag elemezhető és
  összehasonlítható legyen.
- A paraméterezést (P-szabályozó erősítése, keresési szög/sebesség)
  szisztematikus sweep igazolja, nem egyedi kézi próbálgatás.

## Kapcsolódó dokumentumok

- `docs/protocol.md` — TCP/JSON protokoll, benne az `observe`
  válasz szenzormezőinek leírásával (M09 bővítés).
- `docs/sensors.md` — a vonalérzékelő szenzorok kalibrációja és
  zajmodellje.


## Mérési eredmények (első 30 futás)

Az első 30 futást a `reset_position` parancs bevezetése után
végeztük, minden futás elején automatikus pozíció-resettel (azonos
kezdőállapotból indul mindegyik), 300 lépéses felső korláttal.

**Módszertani megjegyzés:** a futások felgyorsítása érdekében a
Unity `Time Scale` beállítását ideiglenesen 70-re emeltük (az
alapértelmezett 1 helyett). Ez csak a valós idő és a szimulált idő
arányát változtatja, a fizikai szimuláció lépésközét nem - a
mérőszámok (parancsszám, vonalvesztés, akadálykerülés,
pályaelhagyás) ettől függetlenek, de jövőbeli munkaként érdemes
alapértelmezett Time Scale mellett is megismételni a mérést,
összehasonlításképp.

**Összegzés (30 futás, `controllers/summarize_runs.py`):**

| Metrika | Átlag | Szórás | Min | Max |
|---|---:|---:|---:|---:|
| Parancsok száma | 746.8 | 31.1 | 625 | 779 |
| Vonalvesztések száma | 14.7 | 3.3 | 11 | 22 |
| Akadálykerülések száma | 3.9 | 4.0 | 0 | 23 |
| Pályaelhagyás | 0/30 futásban | | | |

**Megfigyelések:**
- A baseline kontroller egyetlen futásban sem hagyta el a pályát
  (0/30) - stabil, alapvetően működő vonalkövetés.
- A vonalvesztések száma viszonylag alacsony szórással konzisztens
  (11-22 között).
- Az akadálykerülések száma nagy szórást mutat (0-23), amit
  elsősorban a 14. futás kiugró értéke (23 akadálykerülés) húz fel.
  Ez valószínűleg nem 23 különálló, sikeres elkerülést jelent, hanem
  azt, hogy a rover egy adott futásban egy akadály közelében
  ismételten oda-vissza fordult (oszcillált) anélkül, hogy tisztán
  kikerülte volna - ezt érdemes lesz megvizsgálni és a
  AKADALY_KUSZOB_M/AKADALY_FORDULAT_FOK paraméterek finomhangolásával
  kezelni egy következő iterációban.

## Második mérési sorozat: hiszterézis + nagyobb fordulási szög

A fenti oszcillációs megfigyelés alapján két módosítást vezettünk be:

1. **Hiszterézis** az AKADALY állapotba lépés/kilépés küszöbei közé:
   belépési küszöb maradt 0.5 m, kilépési küszöb 0.8 m-re nőtt (azaz
   csak akkor tér vissza VONALON állapotba, ha az akadály legalább
   0.8 m-re van), hogy elkerüljük a határérték körüli billegést.
2. **Nagyobb AKADALY_FORDULAT_FOK**: 15 fokról 45 fokra növelve,
   hogy egy-egy korrekciós lépés határozottabban kerülje ki az
   akadályt, ne araszoljon el mellette apró lépésekben.

**Összegzés (újabb 30 futás, azonos módszertannal):**

| Metrika | Átlag | Szórás | Min | Max |
|---|---:|---:|---:|---:|
| Parancsok száma | 718.2 | 54.2 | 645 | 794 |
| Vonalvesztések száma | 16.0 | 3.1 | 10 | 24 |
| Akadálykerülések száma | 4.6 | 5.0 | 0 | 12 |
| Pályaelhagyás | 0/30 futásban | | | |

**Őszinte következtetés:** a hiszterézis és a nagyobb fordulási szög
**nem oldotta meg érdemben** a jelenséget - az akadálykerülések
száma továbbra is nagy szórást mutat (0-12), és a nyers adatokban
egyértelműen **kétmodális** eloszlás látszik: a 30 futásból kb.
egyharmada 10-12 körüli, ismétlődő akadálytalálkozást mutat, a
többi pedig 0-1 körülit. Ez arra utal, hogy a probléma gyökere nem
a küszöbérték körüli billegés vagy a fordulási szög mérete volt,
hanem valami strukturálisabb: feltehetően bizonyos megközelítési
szögeknél az elkerülő fordulat visszafordítja a rovert (közvetlenül
vagy a vonalkövetés által korrigálva) ugyanazon vagy egy másik
akadály felé, ismétlődő ciklust okozva.

Ennek pontos diagnosztizálásához **lépésenkénti (nem csak
futás-végi) naplózásra** lenne szükség, ami rögzítené az egyes
lépések szenzor- és LiDAR-adatait, állapotátmeneteit - ez egy
nagyobb műszerezési munka, amit tudatosan **jövőbeli munkaként**
halasztunk, nem ezen mérföldkő részeként.

**Jövőbeli munka (M10 vagy később):**
- Lépésenkénti diagnosztikai naplózás bevezetése (szenzor/LiDAR
  értékek és állapotátmenetek minden lépésnél), hogy a fenti
  kétmodális jelenség gyökere pontosan azonosítható legyen.
- A mérés megismétlése alapértelmezett Time Scale (1) mellett, az
  eredmények összehasonlítása.
- Szisztematikus paraméter-sweep (P-erősítés, keresési szög) a
  fenti diagnosztika birtokában, célzottabban.

## Érvénytelenítés és újramérés (2026-10-06)

**A fenti két 30 futásos sorozat nem igazolja az M09 elfogadási feltételét.**
Fantom-íves pályageometrián készültek (a hibát az M11 tesztjei találták meg),
500 lépéses kerettel, amellyel a teljes kör eleve kizárt volt, és a kanyarban
álló, elfordult kezdőpózból. Az M09-es kapu ezért az alábbi mérésig nyitott.

### Előre rögzített mérési terv

Ez a szakasz a mérés **előtt**, külön commitban került a repóba.

| | |
|---|---|
| Szcenárió | `stadium-train-no-obstacles` (a train pálya akadályok nélkül) |
| Futások száma | 30, egymás után, kihagyás és válogatás nélkül |
| Lépéskeret | 1500 lépés futásonként |
| Kontroller | `controllers/baseline_line_follower.py`, a commitolt paraméterekkel, hangolás nélkül |
| Kezdőpóz | a szcenárió pályájának egyenesén, a vonalon (`reset_position`) |
| Siker egy futásban | legalább egy teljes kör a lépéskereten belül **és** nincs pályaelhagyás |
| Elfogadási küszöb | **legalább 27 sikeres futás a 30-ból (90%)** |

Parancs (a Unityben a `TrackController` *Szcenario Fajl Nev* mezője
`stadium-train-no-obstacles.json`, Play mód, a Unity ablaka előtérben):

```bash
python3 controllers/futtat_kiserletet.py --futasok-szama 30 --max-lepes 1500 \
  --elvart-szcenario stadium-train-no-obstacles
python3 controllers/kor_metrika.py --utolso 30
```

A szcenáriót, a Time Scale-t, a paramétereket és a commitot a futások
metaadat-naplója rögzíti. Ha a küszöb nem teljesül, az eredményt negatív
eredményként közöljük; a sorozatot nem ismételjük meg jobb szám reményében.

### Eredmény (2026-10-06)

**30/30 sikeres futás. Az előre rögzített küszöb (legalább 27/30) teljesült.**

| Metrika | Átlag | Tartomány |
|---|---|---|
| Sikeres futás (teljes kör, pályaelhagyás nélkül) | **30/30** | 95%-os CI: 88,4–100% |
| Pályaelhagyás | 0/30 | |
| Ütközés | 0/30 | |
| Megtett körök 1500 lépés alatt | 2,276 | 2,262 – 2,289 |
| Hatékonyság | 0,986 | 0,984 – 0,989 |
| A vonalon töltött lépések aránya | 65,1% | 56,6% – 73,9% |
| Vonalvesztések száma | 81,3 | 71 – 95 |

Mind a 30 futás azonos beállítással készült: `stadium-train-no-obstacles`,
Time Scale 70, 1500 lépés, `aa06119` commit, tiszta munkakönyvtár.
Futásonkénti metrikák: `docs/m09-ujrameres.json`; metaadatok a
paraméterekkel: `docs/m09-ujrameres-meta.jsonl`. A nyers lépésnapló (92 MB)
a mérete miatt nem kerül a repóba, a következő kiadás mellékleteként lesz
elérhető.

A mérés előtt egy próbafutás készült az eszközök ellenőrzésére, még a
rögzített terv commitja előtt; az nem része a 30-as sorozatnak.

### Korlátok

- **Egy pálya, egy paraméterkészlet.** A kiírás paraméter-sweepet is kér, az
  nincs meg. A dev és a holdout pályán nem mértünk.
- **A vonalkövetés pontatlan.** A rover körbemegy, de a lépések harmadában
  nincs a vonalon. Valószínű ok: a középső színszenzor kb. 11,5 cm-rel el van
  tolva oldalra (élő méréssel megerősítve), ez még nincs javítva.
- **A futások nem bitre azonosak.** A zajgenerátor resetnél újraindul, de a
  szenzorok `FixedUpdate`-enként húznak zajt, a parancsok pedig valós időben
  érkeznek; a nem kinematikus fizika további szórást ad.
- **Time Scale 70.** A mérés gyorsított szimulációban készült.

### Megjegyzés (2026-10-08)

A fenti 30/30 a **javítás előtti** szenzorgeometrián készült (a középső
színszenzor és a LiDAR 11,5 cm-rel oldalra tolva). A szenzorok azóta középre
kerültek, ezért a mérést ugyanezekkel a feltételekkel megismételjük.
