# Megosztható AI-promptok

Ez a mappa a kutatás során használt, érdemi promptokat tartalmazza —
azokat, amelyek egy mérés vagy kiértékelés bemenetét képezték, tehát a
reprodukálhatósághoz hozzátartoznak. A napi fejlesztői beszélgetések
(kódírás, hibakeresés) nem kerülnek ide; azok tanulságai az
`AI_USAGE.md`-ben szerepelnek.

| Fájl | Mérföldkő | Mire használtuk | Kimenet |
|---|---|---|---|
| `m12-vak-api-kiertekeles.md` | M12 | Vak API-használhatósági teszt: az agent forráskód nélkül, csak az MCP-eszközleírásokból vezeti a rovert | `docs/m12/agent-session-raw.txt` |
| `m12-security-review.md` | M12 | Biztonsági átvizsgálás külön AI-munkamenetben | `docs/m12/security-review-raw.txt`, `docs/m12-security-review.md` |

Mindkét prompt önálló, tiszta Claude Code munkamenetben futott (nem
ugyanabban, amelyikben a fejlesztés zajlott), hogy a kiértékelést ne
befolyásolja a korábbi kontextus.
