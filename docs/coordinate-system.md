# Koordinátarendszer és mozgásmodell (M04)

## Mozgásmodell-döntés

A Codex-szel összehasonlítottunk két lehetséges mozgásmodellt:

1. **Kinematikus modell** — a pozíciót közvetlenül a kívánt sebességből
   számoljuk, Rigidbody.MovePosition/MoveRotation segítségével, fizikai
   kerékszimuláció nélkül.
2. **WheelCollider-alapú modell** — valós kerékfizikát (súrlódás,
   felfüggesztés, motor-/féknyomaték) szimulál.

**Döntés:** a projekt a kinematikus modellel indul, mert:
- gyors, determinisztikus, könnyen tesztelhető és hibakereshető
- az AI hibái könnyebben elkülöníthetők a fizikai szimuláció hibáitól
- gyorsabb iterációt tesz lehetővé a vezérlési logika fejlesztésekor

A WheelCollider-alapú modell egy későbbi mérföldkőben, validációs
környezetként kerül majd bevezetésre.

## Vezérlési interfész

### Az M04-es terv

A rover vezérlése ne Unity-specifikus pozícióparancsokkal történjen,
hanem absztrakt sebesség-parancsokkal (`linear_velocity_mps`,
`angular_velocity_radps`), amiket egy adapter fordít le — előbb
MovePosition/MoveRotation műveletekre, később keréknyomatékokra, végül
valódi motorvezérlési parancsokra.

### Ami ténylegesen megvalósult (M05, v1 protokoll)

**Az elv megmaradt, a konkrét mezők viszont mások lettek.** A v1 protokoll
nem folytonos sebesség-parancsokat használ, hanem **diszkrét, befejeződő
mozgásokat**:

| Parancs | Paraméterek |
|---|---|
| `move` | `distance_m`, `max_speed` |
| `turn` | `angle_deg`, `max_angular_speed` |

A `linear_velocity_mps` / `angular_velocity_radps` mezők **soha nem
kerültek be a protokollba**. A váltás oka: a diszkrét, visszajelzéssel
záruló parancsok mellett az állapotgép (IDLE/MOVING/TURNING/ERROR), a
watchdog és az idempotencia-kezelés sokkal egyszerűbben megvalósítható —
egy folytonos sebesség-parancsnál nincs természetes pont, ahol a parancs
"befejeződik".

A mértékegységek és a pontos tartományok: `docs/protocol.md`.

Az absztrakció célja viszont teljesült: a vezérlés nem hivatkozik Unity-
specifikus fogalmakra, így a későbbi WheelCollider-modell vagy fizikai
rover mögé ugyanaz az interfész tehető.

## Koordinátarendszer

- Unity bal-kezes koordinátarendszer: X = jobbra, Y = fel, Z = előre
- A rover "előre" iránya: `transform.forward` (lokális +Z)
- Fordulás: pozitív `angular_velocity_radps` = óramutató járásával
  megegyező irányú fordulás (jobbra), a Unity Y tengelye körül

## Méretek és konvenciók

- Sebesség: m/s (`max_speed`)
- Szög és szögsebesség: fok, illetve fok/s (`angle_deg`,
  `max_angular_speed`) — az M04-es terv még rad/s-ot irányzott elő, a
  megvalósult v1 protokoll fokban dolgozik
- A tényleges méreteket lásd lent

## Rover prefab méretei (tényleges)

- Alváz (RoverChassis): Cube primitíva, Scale **(1, 0.3, 1)**
- Kerekek: Cylinder primitívák, Scale **(0.5, 0.15, 0.5)**,
  Rotation (0, 0, 90)
- Kerék pozíciók (alváz lokális koordinátákban):
  - WheelFrontLeft: (-0.6, 0, 0.4)
  - WheelFrontRight: (0.6, 0, 0.4)
  - WheelBackLeft: (-0.6, 0, -0.4)
  - WheelBackRight: (0.6, 0, -0.4)
- A prefab: `unity/Assets/Prefabs/RoverChassis.prefab`

> **Az alváz Scale Z értéke azért 1.0, nem 1.5.** Az eredeti, M04-es
> geometria 1.5-ös Z-vel készült; az M09-ben kiderült, hogy a túlnyújtott
> alváz miatt a kerekek nekiütköztek az akadályoknak, mielőtt a test
> elfordulhatott volna. A javítás (Z=1.0, kerekek arányosítva) akkor
> **csak a jelenetbeli példányon** történt meg, a prefabon nem: a jelenet
> a javított méreteket prefab-felülírásként (override) tárolja, ezért a
> mérések végig a helyes geometrián futottak, a prefab viszont a régit
> őrizte. (Egy korábbi változat tévesen azt állította, hogy a jelenetbeli
> objektum le lett választva a prefabról.) A prefab 2026-10-06-án lett a
> jelenetbeli, mért geometriához igazítva. A fenti értékek azóta
> mindkettőben azonosak.

