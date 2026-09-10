# M12 terv: agent-interfész (backend-absztrakció, biztonsági réteg, MCP-szerver)

## Cél

Eddig minden kontroller (baseline, replay, kísérletindító) a v1 TCP/JSON
protokollon közvetlenül beszélt a Unity `RoverGatewayServer`-rel. M12
célja egy önálló `adapter/` réteg, ami ez elé áll, és a rovert egy
tetszőleges agent (pl. Claude Code egy MCP-kliensen keresztül) számára
biztonságosan, a szimulátor-részletek elrejtésével teszi elérhetővé -
úgy, hogy az agent a saját szenzoraira legyen utalva, ne egy
privilegizált pozícióadatra.

## Állapot: FOLYAMATBAN

A tervezett munkacsomagok:
1. backend-absztrakció (kész)
2. biztonsági réteg / őrség (kész)
3. MCP-szerver + exportált tool schema (kész)
4. vak API-használhatósági kiértékelés (kész)

## 1-2. munkacsomag: backend-absztrakció és biztonsági réteg (kész)

`adapter/backend.py`: egyetlen `Backend` protokoll (`kuld`/`close`) két
megvalósítással:
- `UnityTcpBackend` - a meglévő v1 TCP/JSON kereten beszél élő
  Unity-vel (4 bájtos hosszfejléc + JSON, ugyanaz, amit a korábbi
  kontrollerek is használnak).
- `MockBackend` - a v1 protokoll állapotgépét, a stadion alakú pálya
  geometriáját (a `TrackController.TavolsagAKozepvonaltol` M11-ben
  javított Python-párja) és a három szín- + lidar-szenzort memóriában
  szimulálja, Unity nélkül. Ez teszi lehetővé, hogy az adapter- és
  MCP-rétegre gyors, determinisztikus tesztek íródjanak, és hogy egy
  agent Unity nélkül is kipróbálhassa az API-t.

`adapter/orseg.py` ("őrség"): az agent és a backend közé ékelődő
biztonsági réteg, a kiírás M12 pontjai szerint:
- csak öt parancsot enged át (`observe`, `move`, `turn`, `stop`,
  `reset_position`) - a `get_status` és `reset_error`, illetve minden
  más v1 parancs le van tiltva;
- minden paramétert a backend **előtt** validál (típus, végesség,
  tartomány) - érvénytelen hívás sosem jut el a roverhez, hanem rövid,
  egyértelmű hibaüzenettel tér vissza (`ADAPTER_*` hibakódok, hogy a
  naplóból egyértelmű legyen, hogy az adapter vagy a v1 protokoll
  utasította-e el a hívást);
- munkamenet-limitek: parancsszám, időtartam, megtett össztávolság;
  bármelyik limit átlépésekor automatikus `stop` és a munkamenet
  lezárása (további hívások `ADAPTER_SESSION_CLOSED`-del elutasítva);
- backend-rejtés: a válaszból eltávolítja a privilegizált
  szimulátor-mezőket (`position`, `speed`, `collision_occurred`,
  `collision_count`, `request_id`) - az agent sosem kap pozícióadatot,
  és abból sem tudja megállapítani, hogy Unity vagy mock áll mögötte.

11 adapter-teszt (`tests/adapter_test.py`) fedi le mindkét réteget
(paraméter-validáció, tartomány-ellenőrzés, session-limitek,
mezőrejtés, engedélyezett/tiltott parancsok) - a `MockBackend`
használatával Unity nélkül futnak, bekerültek a CI-ba (`8689686`:
`adapter/` bevonása a `black` és `pyflakes` ellenőrzésbe is).

## 3. munkacsomag: MCP-szerver és exportált tool schema (kész)

`adapter/mcp_szerver.py`: hat MCP-eszközt regisztrál az `Orseg`
metódusaira építve - `observe`, `move`, `turn`, `stop`,
`reset_position`, `session_status`. Az agent felé csak ez a hat eszköz
látszik; nincs shell- vagy fájlrendszer-hozzáférése, és a
`--backend mock`/`--backend unity` választás a kísérletvezetőé, nem az
agenté - a szerver stderr-jére írja ki, melyik fut, az MCP-csatornára
soha.

A `scripts/export_tool_schema.py` szkript a regisztrált eszközöket (név,
leírás, JSON input-séma) `docs/m12-tool-schema.json`-ba exportálja,
`--ellenoriz` kapcsolóval, ami a fájlt a ténylegesen regisztrált
eszközökhöz hasonlítja (drift-ellenőrzés commit után).

## 4. munkacsomag: vak API-használhatósági kiértékelés (kész)

Egy önálló Claude Code munkamenetet indítottunk azzal az explicit
utasítással, hogy **ne olvassa el a projekt forráskódját**, kizárólag
az MCP-eszközök nevéből és leírásából dolgozzon - mintha egy idegen
roverhez kapott volna hozzáférést -, tartsa a rovert a fehér vonalon kb.
20 lépésen át, majd értékelje az API érthetőségét. A nyers munkamenet-
kimenet: `docs/m12/agent-session-raw.txt`.

Eredmény: mind a 20 lépés `completed` státusszal zárult, elutasított
hívás nem volt (`rejected_calls: 0` a záró `session_status`-ban). A
kiértékelő agent érdemi, dokumentálatlan hiányosságokat talált az
eszközleírásokban:

- a `lidar_szektor_min` leírása közli, hogy a 6 szektor a rover előtti
  180°-os legyezőt fedi le balról jobbra, de nem adja meg, hogy az
  egyes indexek hány fokot ölelnek fel, sem azt, hogy ez hogyan
  viszonyul a három vonalszenzor fizikai irányához - a futás alatt
  végig csak egy szektor (index 3) jelzett csökkenő távolságot, és az
  ügynök nem tudta eldönteni, hogy ez egy valódi akadály volt-e vagy a
  pálya belső íve;
- nincs ajánlott biztonsági küszöb az akadálytávolsághoz - a lépéshossz
  fokozatos csökkentése (0.2 m → 0.03 m) az ügynök saját,
  dokumentálatlan óvatossági döntése volt, nem API-vezérelt;
- a vonalszenzorok csak bináris `white` + `intensity` értéket adnak,
  nincs folytonos "mennyire vagyok a vonal közepén" jelzés; mivel a
  teljes futás alatt mindhárom szenzor állandóan `white:true,
  intensity:1` volt, korrekciós `turn`-re sosem volt szükség, így a
  line-following logika (mikor/mennyit kell fordulni részleges fehér
  esetén) éles helyzetben nem lett kipróbálva;
- nem világos, hogy a `reset_position` beleszámít-e a munkamenet
  parancs-/távolságkeretébe - a leírás csak azt közli, hogy "csak álló
  roveren működik".

Ezek a megfigyelések M12+ dokumentáció-javítási pontok (lidar-szektor
geometria explicit dokumentálása, ajánlott biztonsági küszöb az
eszközleírásban, `reset_position` keret-hatásának tisztázása) -
egyelőre nyitva maradtak, mert a kiértékelés célja a jelenlegi
állapot felmérése volt, nem az API módosítása.

A forráskódhoz hozzáférő fél (nem a kiértékelő ügynök) utólag
ellenőrizte: a futás `MockBackend`-del, `--mock-akadalyokkal`
kapcsolóval történt, és a rover indulási pozíciójából
(`x=4.0, z=0.0`, +z irányba nézve) számolva a 2,6 méteres kezdeti
lidar-érték pontosan megegyezik a `(4.0, 3.0)` pontra helyezett,
0,4 m sugarú mock-akadályig mért távolsággal. Tehát a kiértékelő
ügynök elé valóban egy szándékosan elhelyezett akadály került a
pálya közepén, nem a pálya belső íve - az, hogy ezt a leírásokból
nem lehetett egyértelműen megállapítani, egy valódi, nem csak
hipotetikus dokumentációs hiányosságot igazol.

## Talált és javított hiba: `.venv` véletlen verziókövetése

A 3. munkacsomag commitjakor (`172b7fe`) a teljes Python virtualenv
(3207 fájl, ~90 MB, fordított binárisokkal együtt) véletlenül
bekerült a git indexbe, mert a `.venv/` sosem volt a `.gitignore`-ban,
és már fel is lett push-olva. Javítás (`9d526b3`): `.venv/`,
`__pycache__/` és `*.pyc` felvétele a `.gitignore`-ba, majd
`git rm -r --cached` a már trackelt példányokra - a history-ban a
blob-ok megmaradnak, de a HEAD és az új klónok innentől tiszták.
Történeti purge (pl. `git filter-repo` + force-push) tudatosan nem
történt, mert az megosztott history-t írna felül.

## Hátralévő munkacsomagok

Nincs - mind a négy munkacsomag kész. Lezáráskor (tag, README,
CITATION, AI_USAGE.md) a szokásos M-sorozat mintát követjük.

## 5. munkacsomag: biztonsági átvizsgálás (kész)

Külön AI-munkamenetben végzett security review (`docs/m12-security-review.md`,
nyers kimenet: `docs/m12/security-review-raw.txt`): 8 találat, ebből 5 javítva
kódban vagy dokumentációban, 2 nyitva hagyva M13+-ra, 1 megfigyelés. A vak
kiértékelés három dokumentációs hiányossága is javítva az eszközleírásokban.
A javításokhoz 7 regressziós teszt készült (`tests/adapter_test.py`, összesen 18).

Nyitott, M13+ pontok:
- az időkorlát csak parancsok között ellenőrződik, egy hosszú blokkoló `move`
  a limit fölé viheti a tényleges munkamenet-időt (watchdog-szál kellene);
- a backend típusa válaszidőből kikövetkeztethető (a mock azonnal válaszol,
  a Unity a mozgás idejéig blokkol) - elvi korlát;
- a mock backend "túl kényelmes": a vak futás alatt a rover végig tökéletesen
  a vonal közepén maradt, ezért a korrekciós logika nem került próbára;
- egy második vak kiértékelés valódi kanyarban/részleges fehér
  esetén, hogy a line-following korrekciós logika (`turn` időzítése)
  is kipróbálásra kerüljön - a jelen futás alatt a vonal végig
  tökéletesen középen volt, így ez nem derült ki;
- Unity backenddel is megismételni a vak kiértékelést (a jelen futás
  mock backenddel történt).
