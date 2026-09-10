# M12: biztonsági átvizsgálás (security review)

**Mérföldkő:** M12 (agent-facing MCP adapter)
**Munkamenet:** külön, tiszta Claude Code session, forráskód-olvasással
**Dátum:** 2026-09-10
**Nyers kimenet:** `docs/m12/security-review-raw.txt`
**Összefoglaló:** `docs/m12-security-review.md`

## Cél

A kiírás M12-es kötelező AI-használati pontja szerint az adaptert egy
külön AI-munkamenetnek kell átvizsgálnia. A vak kiértékeléssel
ellentétben itt az agent **elolvassa** a forráskódot, és
támadó/hibakereső szemszögből kritizálja a saját maga (illetve a hasonló
agentek) számára készült API-t.

## Prompt

> Az adapter/ mappában egy MCP-adapter van, ami egy fizikai roverhez ad
> hozzáférést AI-agenteknek (adapter/backend.py, adapter/orseg.py,
> adapter/mcp_szerver.py). Olvasd el ezeket a fájlokat, és készíts
> biztonsági átvizsgálást. Konkrétan keresd: (1) mivel tudna egy
> rosszindulatú vagy hibás agent kárt okozni a roverben vagy a
> környezetében, (2) hol lehet megkerülni a session-limiteket vagy a
> paraméter-validációt, (3) hol félreérthető vagy hiányos az
> eszközleírás úgy, hogy az veszélyes viselkedéshez vezethet, (4)
> szivárog-e ki bármi, aminek rejtve kellene maradnia az agent elől.
> Minden találatnál add meg a fájlt és a sort, a kockázat súlyosságát, és
> egy konkrét javítási javaslatot. Ne módosítsd a kódot, csak írd le a
> megállapításokat.

## Eredmény

Nyolc találat (2 magas, 3 közepes, 3 alacsony/megfigyelés). Öt javítva,
kettő nyitva M13+-ra, egy megfigyelés. A találatok egyikét sem fogta meg
a 11 meglévő unit teszt; a javításokhoz 7 regressziós teszt készült.
Részletek: `docs/m12-security-review.md`.
