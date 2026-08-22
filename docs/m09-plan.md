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

**Jövőbeli munka:**
- Az akadály-oszcilláció kivizsgálása és kezelése (pl. hiszterézis
  bevezetése az AKADALY állapotba lépés/kilépés küszöbei közé).
- A mérés megismétlése alapértelmezett Time Scale (1) mellett, az
  eredmények összehasonlítása.
- Szisztematikus paraméter-sweep (P-erősítés, keresési/akadály-
  fordulási szögek) a docs/m09-plan.md tervezett módszertana szerint.
