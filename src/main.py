"""Codex próbafeladatok - 3 kis gyakorlófeladat."""

import argparse
import csv


# 1. feladat: Prímszám-ellenőrzés
def prim_e(szam: int) -> bool:
    if szam < 2:
        return False

    oszto = 2
    while oszto * oszto <= szam:
        if szam % oszto == 0:
            return False
        oszto += 1

    return True


# 2. feladat: Mérési adatok kiértékelése (átlag, minimum, maximum)
def meresek_kiertékelese(adatok: list[float], mertekegyseg: str) -> None:
    if not adatok:
        print("Nincsenek kiértékelhető mérési adatok.")
        return

    atlag = sum(adatok) / len(adatok)

    print("Mérési eredmények")
    print("------------------")
    print(f"Mérések száma: {len(adatok)}")
    print(f"Átlag:         {atlag:.2f} {mertekegyseg}")
    print(f"Minimum:       {min(adatok):.2f} {mertekegyseg}")
    print(f"Maximum:       {max(adatok):.2f} {mertekegyseg}")


# 3. feladat: CSV-fájl első sorainak megjelenítése
def csv_elso_sorai(fajlnev: str) -> None:
    try:
        with open(fajlnev, encoding="utf-8-sig", newline="") as fajl:
            olvaso = csv.reader(fajl)
            oszlopok = next(olvaso, None)

            if oszlopok is None:
                print("A CSV-fájl üres.")
                return

            print("Oszlopok:")
            print(", ".join(oszlopok))
            print("\nAz első 5 sor:")

            sorok_szama = 0
            for sorok_szama, sor in enumerate(olvaso, start=1):
                if sorok_szama > 5:
                    break
                print(f"{sorok_szama}. {', '.join(sor)}")

            if sorok_szama == 0:
                print("Nincsenek adatsorok.")
    except FileNotFoundError:
        print(f"Hiba: nem található a fájl: {fajlnev}")
    except (OSError, UnicodeError, csv.Error) as hiba:
        print(f"Hiba a CSV-fájl olvasásakor: {hiba}")


if __name__ == "__main__":
    print("=== 1. feladat: Prímszám-ellenőrzés ===")
    teszt_szamok = [1, 2, 7, 17, 20, 25]
    for szam in teszt_szamok:
        eredmeny = "prímszám" if prim_e(szam) else "nem prímszám"
        print(f"{szam}: {eredmeny}")

    print("\n=== 2. feladat: Mérési adatok kiértékelése ===")
    testhomersekletek = [36.5, 36.8, 37.2, 36.7, 37.0]
    meresek_kiertékelese(testhomersekletek, "°C")

    print("\n=== 3. feladat: CSV beolvasás ===")
    parser = argparse.ArgumentParser(description="CSV-fájl tartalmának bemutatása")
    parser.add_argument("fajl", nargs="?", default="meresi_adatok.csv")
    argumentumok = parser.parse_args()
    csv_elso_sorai(argumentumok.fajl)
