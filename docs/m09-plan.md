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
