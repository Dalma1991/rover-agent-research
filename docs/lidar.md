# 2D LiDAR-szimuláció (M08)

## LiDAR-modell

A `LidarSensor.cs` egy egyszerűsített, vízszintes síkú, legyező alakú
raycast-LiDAR-t szimulál:

1. A `transform.forward` körül, `Latomezo Fok` fokos látómezőben,
   `Sugar Szam` db egyenletesen elosztott sugarat indít minden
   `FixedUpdate`-ben (`Frissites Ritkitasa`-val ritkítható).
2. Minden sugárhoz `Physics.Raycast`-tel lekérdezi a legközelebbi
   találatot az `Akadaly Reteg` rétegmaszkon belül, `Max Hatotav`-ig.
3. A nyers távolságokat (`NyersTavolsagok[]`) és az érvényességi
   maszkot (`ErvenyessegiMaszk[]`) teszi elérhetővé.
4. A sugarakat `Szektor Szam` db szektorba csoportosítja, és
   szektoronként Min/Átlag távolságot számol
   (`SzektorMinTavolsag[]` / `SzektorAtlagTavolsag[]`) — ez egy
   tömörített, alacsonyabb dimenziós alternatíva a nyers jelhez
   képest.

Opcionálisan (`Zaj Szoras Meter`, `Meres Kimaradas Eselye`, `Keses
Fixed Update Keretekben`) Gauss-zajt, soronkénti méréskimaradást és
mesterséges késleltetést szimulál, ugyanazzal a Box-Muller-alapú
zajgenerátorral és seedelt `System.Random`-mal, mint a `ColorSensor.cs`
(lásd `docs/sensors.md`).

## Geometriai pontosság-teszt

A `Max Hatotav`-on belüli távolságmérés pontosságát ismert pozícióban
elhelyezett akadállyal igazoltuk. Mivel a tesztakadály egy 1×1×1
méteres kocka, a sugár a **felületét** találja el, nem a
középpontját — az elvárt mért távolság ezért mindig a középpont
távolsága mínusz a kocka fél-mérete (0.5 m).

A tesztet két lépésben végeztük el:

### 1. Elvi validáció (különálló, "tiszta" tesztobjektumon)

Egy transzformáció nélküli (`Position`/`Rotation` = 0) segédobjektumon
(`LidarSensor` komponenssel), hogy kiküszöböljük a `RoverChassis`
összetett, nem egyenletes skálázásából eredő zavaró tényezőket:

| Kocka középpont (Z) | Elvárt felület-táv. | Mért érték |
|---|---|---|
| 1 | 0.5 m | 0.484 m |
| 2 | 1.5 m | 1.500 m |
| 3 | 2.5 m | 2.506 m |
| 5 | 4.5 m | 4.489 m |
| 8 | 7.5 m | 7.488 m |

### 2. Megerősítés az éles, roveren beépített szenzoron

Ugyanezt a tesztet megismételtük a `RoverChassis` alatti, éles
`Lidar` GameObject-tel is, a tesztakadályt a rover és a szenzor
tényleges világkoordinátáiból kiszámolt pozíciókba helyezve:

| Elvárt felület-táv. | Mért érték |
|---|---|
| 0.5 m | 0.497 m |
| 1.5 m | 1.497 m |
| 2.5 m | 2.517 m |
| 4.5 m | 4.521 m |
| 7.5 m | 7.457 m |

Mindkét tesztsorozatban minden eltérés a beállított **0.02 m**-es
Gauss-zaj szórás ésszerű tartományán belül maradt — a geometriai
pontosság igazolt, mind elvi, mind a végleges, beépített
konfigurációban.

## Réteg-kizárás (self-collision elkerülése)

Mivel a `Lidar` a `RoverChassis` gyereke, az alapértelmezett
`Everything` rétegmaszk mellett a sugarak a rover saját dobozütközőjébe
ütköztek volna. Ennek elkerülésére létrehoztunk egy külön **"Rover"**
Unity-réteget, ráállítottuk a `RoverChassis` objektumra (csak a
chassis-ra, nem a gyerekeire), és az `Akadaly Reteg` mezőből kizártuk
ezt a réteget. Ez ugyanaz a mintázat, mint amikor egy valódi LiDAR
telepítésekor figyelni kell arra, hogy a szenzor ne "lássa" a saját
tartókeretét.

## Futásidő-profilozás

A `LidarSensor` minden mérés futási idejét méri (`System.Diagnostics.
Stopwatch`), `UtolsoMeresIdejeMs` / `AtlagMeresIdejeMs` property-ken
keresztül elérhetően. Négy felbontásnál mértük a mérési időt az éles,
roveren beépített szenzoron:

| Sugár szám | Mérési idő |
|---|---|
| 12 | 0.040 ms |
| 36 | 0.075 ms |
| 72 | 0.137 ms |
| 144 | 0.239 ms |

A futásidő **közel lineárisan** skálázódik a sugárszámmal (12-szeres
sugárszám-növelés ~6-szoros időnövekedést okozott) — nincs
szuperlineáris lassulás, a raycast-alapú módszer jól skálázódik a
felbontással. A projekt éles beállítása (36 sugár, 180°) jóval a
valós idejű futtatás költségvetésén belül marad.

## Szektoros tömörítés

A `Szektor Szam = 6` alapértelmezett beállítás mellett a 36 nyers
sugarat 6 db, egyenként 6 sugarat összefogó szektorra bontja, és
szektoronként Min/Átlag távolságot számol. Ez egy egyszerű, olcsó
adatkompressziós alternatíva a nyers jelhez képest — jövőbeli
mérföldkövekben (pl. akadálykerülő algoritmus) hasznos lehet, ha a
teljes nyers sugárvektor helyett elég a durvább, szektoronkénti kép.
