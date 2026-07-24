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

A rover vezérlése nem Unity-specifikus pozícióparancsokkal történik,
hanem absztrakt sebesség-parancsokkal:

```json
{
  "linear_velocity_mps": 1.0,
  "angular_velocity_radps": 0.3
}
```

Ezt egy külön adapter fordítja le:
- jelenleg: MovePosition/MoveRotation műveletekre (kinematikus modell)
- később: keréknyomatékokra és kormányzásra (WheelCollider modell)
- végül: valódi motorvezérlési parancsokra (fizikai rover)

## Koordinátarendszer

- Unity bal-kezes koordinátarendszer: X = jobbra, Y = fel, Z = előre
- A rover "előre" iránya: `transform.forward` (lokális +Z)
- Fordulás: pozitív `angular_velocity_radps` = óramutató járásával
  megegyező irányú fordulás (jobbra), a Unity Y tengelye körül

## Méretek és konvenciók

- Alváz méretei: (később, a prefab elkészülte után dokumentálva)
- Sebesség mértékegysége: m/s
- Szögsebesség mértékegysége: rad/s

## Rover prefab méretei (tényleges)

- Alváz (RoverChassis): Cube primitíva, Scale (1.0, 0.3, 1.5)
- Kerekek: Cylinder primitívák, Scale (0.3, 0.6, 0.3), Rotation (0, 0, 90)
- Kerék pozíciók (alváz lokális koordinátákban):
  - WheelFrontLeft: (-0.6, 0.3, 0.6)
  - WheelFrontRight: (0.6, 0.3, 0.6)
  - WheelBackLeft: (-0.6, 0.3, -0.6)
  - WheelBackRight: (0.6, 0.3, -0.6)
- A prefab: Assets/Prefabs/RoverChassis.prefab
