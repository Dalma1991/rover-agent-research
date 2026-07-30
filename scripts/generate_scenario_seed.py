#!/usr/bin/env python3
"""Reprodukálható uint32 seed képzése szcenárió-azonosítóból."""

from __future__ import annotations

import argparse
import hashlib


def scenario_seed(scenario_type: str, name: str) -> int:
    canonical_id = f"{scenario_type}:{name}".encode("utf-8")
    digest = hashlib.sha256(canonical_id).digest()
    return int.from_bytes(digest[:4], byteorder="big", signed=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario_type", choices=("train", "dev", "test"))
    parser.add_argument("name")
    args = parser.parse_args()
    print(scenario_seed(args.scenario_type, args.name))


if __name__ == "__main__":
    main()
