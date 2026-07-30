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
