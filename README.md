# codex-proba-feladatok

Kutatási célú projekt a Codex CLI/IDE-integráció kipróbálására.

## Tartalom
- `src/` — a Codex-szel generált próbakódok
- `scripts/doctor` — verzió- és függőségellenőrző script
- `unity-projekt/` — üres Unity projekt (URP sablon)
- `INSTALL_CHECKLIST.md` — lépésről lépésre telepítési ellenőrzőlista
- `ENVIRONMENT.md` — a fejlesztői környezet leírása
- `AI_USAGE.md` — a Codex-szel végzett munka naplója
- `docs/screenshots/` — képernyőképek a mérföldkövekhez

## Telepítés
A projekt telepítéséhez és ellenőrzéséhez kövesd az [INSTALL_CHECKLIST.md](INSTALL_CHECKLIST.md)
fájlban leírt lépéseket, majd futtasd a `scripts/doctor` szkriptet a környezet
ellenőrzéséhez:

```bash
./scripts/doctor
```

## Cél
A projekt célja, hogy kipróbáljam a Codexet mint AI kódoló asszisztenst,
és dokumentáljam a használat tapasztalatait az `AI_USAGE.md` fájlban.

## Mérföldkövek
- **m01**: friss klónból megnyitható Unity projekt, futó Python környezet,
  legalább egy ellenőrzött Codex-módosítás.
