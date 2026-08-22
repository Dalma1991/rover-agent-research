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
