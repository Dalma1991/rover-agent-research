# rover-agent-research

Kutatási projekt: *Simulation-Blind Two-Timescale Rover Control by
General-Purpose Coding Agents*. Codex CLI/IDE-integrációval támogatott
fejlesztés.

## Tartalom
- `unity/` — Unity szimulációs projekt
- `gateway/` — Python CLI kliens a rover API-hoz
- `controllers/` — baseline, agent-generated és hybrid controllerek (később)
- `training/`, `models/` — neurális policy tanítása (később)
- `experiments/` — kísérleti konfigurációk, seedek (később)
- `tests/` — integrációs és regressziós tesztek
- `docs/` — architektúra, protokoll, döntési napló, képernyőképek, videók
- `paper/` — az angol nyelvű cikk forrása (később)
- `prompts/` — lényeges, megosztható AI-promptok
- `scripts/doctor` — verzió- és függőségellenőrző script
- `INSTALL_CHECKLIST.md` — lépésről lépésre telepítési ellenőrzőlista
- `ENVIRONMENT.md` — a fejlesztői környezet leírása
- `AI_USAGE.md` — a Codex-szel végzett munka naplója

## Telepítés
A projekt telepítéséhez és ellenőrzéséhez kövesd az [INSTALL_CHECKLIST.md](INSTALL_CHECKLIST.md)
fájlban leírt lépéseket, majd futtasd a `scripts/doctor` szkriptet a környezet
ellenőrzéséhez:

```bash
./scripts/doctor
```

## Rover Gateway kipróbálása
1. Nyisd meg a `unity/` Unity projektet, töltsd be a `NetworkControlScene`-t
2. Nyomj Play-t (a szerver elindul a 127.0.0.1:8765 porton)
3. Terminálban: `python3 gateway/client.py`
4. Próbáld ki: `observe`, `move <táv> <sebesség>`, `stop`

## Cél
A projekt célja egy reprodukálható kutatási platform felépítése, amelyben
egy rover Unity-szimulációban, majd később fizikai környezetben is
irányítható egy egységes, külső szenzor-akció interfészen keresztül —
hagyományos algoritmussal, AI coding agenttel, agent által generált
controllerrel és neurális policy-vel egyaránt.

## Mérföldkövek
- **m01**: friss klónból megnyitható Unity projekt, futó Python környezet,
  legalább egy ellenőrzött Codex-módosítás.
- **m02**: mozgó gömb Unityben, billentyűzetes vezérléssel, Play Mode
  tesztekkel.
- **m03**: a gömb külső, TCP/JSON alapú vezérlése Python CLI kliensből.
- **m04**: roverszerű, négykerekű kinematikus objektum és prefab,
  determinisztikus mozgással.
- **m05**: formális roverprotokoll (v1), JSON séma, hibakódok, állapotgép,
  biztonsági korlátok (sebesség/távolság/szög/timeout), idempotencia,
  fuzz/property-based tesztek.
- **m06**: zárt, stadion alakú pálya fehér vonallal, paraméterezhető
  geometriával (egyenes hossz, kanyar sugár, vonalszélesség, háttérszín),
  seedelt determinisztikus akadályütemezés, train/dev/test szcenáriók.
- **m07**: vonalérzékelő szenzorok (raycast + zaj + küszöb modell),
  mérés alapján kalibrált küszöb, kapcsolható egy-/háromszenzoros
  (bal-közép-jobb) mód, reprodukálható zaj-seedek.
- **m08**: 2D LiDAR-szimuláció (raycast-alapú, konfigurálható
  látómező/felbontás/hatótáv), szektoros tömörítés, zaj/dropout/
  késleltetés-modellezés, geometriai kalibráció ismert pozíciókban,
  futásidő-profilozás több felbontásnál.
- **m09**: hagyományos (AI nélküli) vonalkövető baseline kontroller
  (állapotgép + P-szabályozó), LiDAR-alapú akadályelkerülés, uj
  `reset_position` protokollparancs a reprodukálható mérésekhez,
  két 30 futásos mérési sorozat (0/30 és 0/30 pályaelhagyás),
  dokumentált nyitott kérdéssel az akadálykerülés kétmodális
  eloszlásáról (lásd docs/m09-plan.md).
- **m10**: ütközésdetektálás (`OnCollisionEnter`, időalapú cooldown
  a többszörös számlálás ellen), lépésenkénti diagnosztikai naplózás,
  irányított vonal-visszakeresés akadálykerülés után (`VISSZATALALAS`
  állapot, 11/11 sikeres Unity Play mód-os teszten), explicit
  zsákutca-észlelés és -eszkalálás, javított akadály-időzítés
  (`reset_position`-höz kötve, nem a Play mód indításához) - végleges
  30 futásos mérés dokumentált nyitott kérdéssel az M09-ben azonosított
  oszcillációs probléma további megerősítéséről (lásd docs/m10-plan.md).
- **m10.5** (nem hivatalos, utólagos finomítás): az M09/M10-ben
  dokumentált oszcillációs jelenség gyökérokának feltárása és
  javítása - az AKADALY állapot mostantól ténylegesen halad is
  előre a fordulás közben, és az `AKADALY_KUSZOB_KILEPES_M`
  paraméter finomhangolva (1.1). Eredmény: pályaelhagyás 60%->0%,
  átlagos ütközésszám 20.9->10.2 (30 futásos méréssel igazolva).
  Két elvetett javítási kísérlet is dokumentálva (lásd
  docs/m10-5-plan.md).
