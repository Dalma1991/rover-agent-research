#!/usr/bin/env python3
"""Dokumentacio-ellenorzes (M11 CI): a README.md, REPRODUCIBILITY.md es a
docs/*.md fajlokban backtick kozott hivatkozott repo-beli utvonalak
leteznek-e. Csak olyan hivatkozasokat vizsgal, amelyek egyertelmuen
fajlutvonalnak neznek ki (tartalmaznak '/'-t vagy ismert kiterjesztest,
es nem parancsok). Hianyzo fajl eseten nem-nulla kilepesi kod."""

from __future__ import annotations

import re
from pathlib import Path

GYOKER = Path(__file__).resolve().parent.parent
FAJLOK = [GYOKER / "README.md", GYOKER / "REPRODUCIBILITY.md", *sorted((GYOKER / "docs").glob("*.md"))]
MINTA = re.compile(r"`([A-Za-z0-9_./-]+\.(?:py|md|cs|json|yml|yaml|cff|svg|png|mov|mp4|jsonl|unity|prefab|asmdef))`")
KIHAGY = ("http", "*")


def main() -> int:
    hianyzo: list[tuple[Path, str]] = []
    ellenorzott = 0
    for md in FAJLOK:
        for hivatkozas in MINTA.findall(md.read_text(encoding="utf-8")):
            if any(k in hivatkozas for k in KIHAGY) or "/" not in hivatkozas:
                continue
            ellenorzott += 1
            if not (GYOKER / hivatkozas).exists():
                hianyzo.append((md.relative_to(GYOKER), hivatkozas))
    print(f"{ellenorzott} hivatkozas ellenorizve {len(FAJLOK)} dokumentumban.")
    if hianyzo:
        print("HIANYZO fajlok:")
        for md, h in hianyzo:
            print(f"  {md}: {h}")
        return 1
    print("OK: minden hivatkozott fajl letezik.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
