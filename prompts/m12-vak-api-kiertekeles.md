# M12: vak API-használhatósági kiértékelés

**Mérföldkő:** M12 (agent-facing MCP adapter)
**Munkamenet:** külön, tiszta Claude Code session, `rover` MCP-szerver
mock backenddel (`--backend mock --mock-akadalyokkal`)
**Dátum:** 2026-09-10
**Nyers kimenet:** `docs/m12/agent-session-raw.txt`

## Cél

Megmérni, hogy az MCP-eszközök **neve és leírása önmagában** elegendő-e
egy agentnek a rover vezérléséhez, forráskód-hozzáférés nélkül. Ha az
agent elolvashatná az `adapter/` forrását, nem az API dokumentációját
mérnénk, hanem a kódértési képességét.

## Prompt

> A `rover` MCP-szerveren keresztül egy vonalkövető robotot vezérelsz egy
> stadion alakú pályán. Ne olvasd el a projekt forráskódját — kizárólag az
> MCP-eszközök nevéből és leírásából dolgozz, mintha egy idegen roverhez
> kaptál volna hozzáférést. Feladat: tartsd a rovert a fehér vonalon, és
> haladj előre kb. 20 lépésen keresztül. Minden lépés előtt olvasd le a
> szenzorokat, és abból döntsd el a következő parancsot. A végén hívd meg
> a session_status-t. Utána írj egy rövid értékelést: mennyire volt
> érthető az API a leírásokból, mi volt félreérthető, mit hiányoltál, és
> melyik hívásod akadt el (ha volt ilyen) és miért.

## Eredmény

20 lépés lefutott, 0 elutasított hívás. Az agent négy dokumentációs
hiányt azonosított (lidar-szektorok szöggeometriája, hiányzó biztonsági
küszöb, folytonos vonalpozíció-jelzés hiánya, `reset_position`
keret-hatása) — ebből három javítva az M12-ben, a negyedik nyitva
maradt, mert a mock backenden a rover végig a vonal közepén haladt, így
a korrekciós logika nem került próbára.
