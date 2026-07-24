# AI eszközök használata

## Codex (CLI/IDE integráció)
- **Eszköz:** Codex, PyCharm IDE-integráció
- **Cél:** kódrészletek generálása és kipróbálása

## Elvégzett próbafeladatok

### 1. Prímszám-ellenőrzés
A Codex-szel generáltattam egy `prim_e()` függvényt, ami eldönti egy számról,
hogy prímszám-e. A kódot néhány teszt-számmal (1, 2, 7, 17, 20, 25) ki is
próbáltam.

### 2. Mérési adatok kiértékelése
A Codex-szel generáltattam egy `meresek_kiertékelese()` függvényt, ami egy
számlistából (pl. testhőmérséklet-adatok) kiszámolja az átlagot, a minimumot
és a maximumot, majd szépen kiírja az eredményt.

### 3. CSV-fájl beolvasása
A Codex-szel generáltattam egy `csv_elso_sorai()` függvényt, ami beolvas egy
CSV-fájlt, kiírja az oszlopneveket, majd megjeleníti az első 5 adatsort.
Hibakezelést is tartalmaz (pl. ha a fájl nem található).

### 4. Telepítési ellenőrzőlista (INSTALL_CHECKLIST.md)
A Codex-szel generáltattam egy lépésről lépésre követhető, kipipálható telepítési
ellenőrzőlistát, ami leírja a Git, Unity 6000.3.20f1 LTS és Python 3.9 telepítését,
a virtuális környezet létrehozását, valamint a `scripts/doctor` futtatását
ellenőrzésképp. A listát friss klónból végig is teszteltem.

### 5. scripts/doctor bővítése
A Codex-szel generáltattam egy `scripts/doctor` nevű ellenőrző szkriptet, ami
kiírja a Python, Git és Pip verzióját, ellenőrzi a szükséges Python modulokat
(argparse, csv), és megnézi, hogy a projekt alapfájljai (src/main.py, README.md,
AI_USAGE.md) megvannak-e.

### 6. Unity mozgó gömb komponens (MovementController.cs)
A Codex-szel megíratattam a MovementController.cs C# komponenst, ami a
WASD/nyílbillentyűkkel mozgatja a gömböt egy Rigidbody segítségével.
A komponens tartalmaz egy Inspectorból állítható sebességparamétert,
egy R billentyűre aktiválódó reset funkciót, és egyszerű ütközésjelzést.
A Codex részletesen elmagyarázta a MonoBehaviour, Update és FixedUpdate
szerepét: a bemenet olvasása az Update-ben történik (képkockánként fut),
míg a fizikai mozgatás a FixedUpdate-ben (rögzített időközönként, a
Unity fizikai motorjához igazodva).

### 7. Play Mode tesztek
A Codex 3 lehetséges tesztelési megközelítést javasolt a mozgás és a
reset ellenőrzésére: (1) publikus metódus közvetlen tesztelése,
(2) bemeneti rendszer szimulálása, (3) Rigidbody közvetlen tesztelése.
A publikus metódus (Move()) közvetlen tesztelése mellett döntöttem,
mert stabil, gyors és nem függ az Input System konfigurációjától.
A Codex ez alapján megírta a MovementControllerPlayModeTests.cs
fájlt, ami két tesztet tartalmaz: a mozgás- és a reset-funkció
ellenőrzését. Mindkét teszt sikeresen lefutott.

## Megjegyzések
Az AI (Codex) által generált kódot mindegyik esetben átnéztem és kipróbáltam,
mielőtt bekerült a `src/main.py` fájlba.
