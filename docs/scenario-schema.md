# Stadionpálya-szcenáriók

Ez a dokumentum a zárt, stadion alakú roverpályák JSON-formátumát írja
le. A géppel ellenőrizhető definíció a
[`scenario.schema.json`](scenario.schema.json) fájlban található, a
példák pedig az `experiments/scenarios/` könyvtárban vannak.

## Koordináták és mértékegységek

A formátum a `coordinate-system.md` Unity-konvencióit követi:

- X jobbra, Y felfelé, Z előre mutat;
- minden hossz és pozíció méterben, minden idő másodpercben értendő;
- a pálya origója a stadion közepe a talaj síkján (`y = 0`);
- a két egyenes középvonala a Z tengellyel párhuzamos, `x =
  ±turn_radius_m` mellett, `-straight_length_m / 2` és
  `+straight_length_m / 2` között;
- a két félkör középpontja `(0, 0, ±straight_length_m / 2)`, sugara
  `turn_radius_m`.

Az akadályok tengelyekkel párhuzamos téglatestek. A `position_m` a téglatest
középpontja, a `size_m` pedig a teljes X/Y/Z kiterjedése. Talajon álló
akadálynál ezért `position_m.y = size_m.y / 2`.

## Dokumentumszerkezet

A gyökérobjektum négy kötelező része:

- `schema_version`: jelenleg mindig `"1.0"`;
- `metadata`: a stabil `name`, a `train`, `dev` vagy `test` adathalmazt jelölő
  `type`, valamint egy unsigned 32 bites `seed`;
- `track`: az egyenes hossza, a kanyar középvonalának sugara, a vonal
  szélessége és a háttér 0–255 tartományú RGB-komponensei;
- `obstacles`: nulla vagy több, egyedi `id`-jú téglatest.

A séma zárt: a nem dokumentált mezőket az `additionalProperties: false`
elutasítja. A JSON-számoknak végesnek kell lenniük; `NaN` és `Infinity`
nem szabványos JSON-érték.

## Akadályütemezés

Minden akadály `schedule` objektuma megadja:

- `appear_at_s`: megjelenés ideje a szcenárió indulásától;
- `visible_for_s`: a láthatóság időtartama;
- `disappear_at_s`: az eltűnés ideje.

Az akadály az `[appear_at_s, disappear_at_s)` félig nyílt intervallumban
aktív. Kötelező szemantikai invariáns:

```text
disappear_at_s = appear_at_s + visible_for_s
```

A JSON Schema a mezők típusát és tartományát ellenőrzi; ezt a mezők
közötti egyenlőséget, az akadályazonosítók egyediségét és a fizikai
pályán belüli elhelyezést a betöltőnek is ellenőriznie kell.

## Determinisztikus seedelés és generálás

A seedet nem kézzel választjuk. A `scripts/generate_scenario_seed.py` a
kanonikus `type:name` UTF-8 szöveg SHA-256 hashének első négy bájtját
unsigned, big-endian 32 bites egészként értelmezi:

```bash
python3 scripts/generate_scenario_seed.py train stadium-train-baseline
```

Az azonos típus és név mindig ugyanazt a seedet adja. A név vagy az
adathalmaztípus megváltoztatása új seedet eredményez, ezáltal a train/dev/test
szcenáriók véletlen sorozatai elkülönülnek.

A példák akadályait a `scripts/generate_example_scenarios.py` állítja elő.
Minden mintához a `seed:mező-címke` SHA-256 hash első 64 bitjéből képez
egy `[0, 1]` intervallumú értéket, majd ezt vetíti a dokumentált pozíció-,
méret- és időtartományokra. Ez számlálóalapú, platformfüggetlen
generálás: nem támaszkodik a Python `random` moduljának belső állapotára.

Az összes példa újragenerálása:

```bash
python3 scripts/generate_example_scenarios.py
```

Az elkészülő példák:

- `stadium-train-baseline.json`;
- `stadium-dev-scheduled.json`;
- `stadium-test-hidden.json`.

Az explicit akadálylista a generálás rögzített eredménye. A futtatónak
nem szabad azt betöltéskor újragenerálnia; a seed a reprodukálhatóságot és
a generálási eredet ellenőrizhetőségét biztosítja.
