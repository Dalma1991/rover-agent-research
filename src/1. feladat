"""1. feladat: Prímszám-ellenőrzés."""


def prim_e(szam: int) -> bool:
    if szam < 2:
        return False

    oszto = 2
    while oszto * oszto <= szam:
        if szam % oszto == 0:
            return False
        oszto += 1

    return True


if __name__ == "__main__":
    teszt_szamok = [1, 2, 7, 17, 20, 25]

    for szam in teszt_szamok:
        eredmeny = "prímszám" if prim_e(szam) else "nem prímszám"
        print(f"{szam}: {eredmeny}")
