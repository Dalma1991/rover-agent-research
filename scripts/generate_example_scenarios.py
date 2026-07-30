#!/usr/bin/env python3
"""A dokumentált példaszcenáriók determinisztikus előállítása."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from generate_scenario_seed import scenario_seed


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "experiments" / "scenarios"

SCENARIOS = (
    ("train", "stadium-train-baseline", 12.0, 4.0, 0.18, (28, 32, 28), 2),
    ("dev", "stadium-dev-scheduled", 10.0, 3.5, 0.20, (35, 38, 42), 1),
    ("test", "stadium-test-hidden", 14.0, 4.5, 0.16, (22, 25, 31), 2),
)


def sample(seed: int, label: str) -> float:
    payload = f"{seed}:{label}".encode("utf-8")
    integer = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")
    return integer / ((1 << 64) - 1)


def between(seed: int, label: str, minimum: float, maximum: float) -> float:
    return round(minimum + sample(seed, label) * (maximum - minimum), 3)


def obstacle(seed: int, prefix: str, index: int, length: float, radius: float) -> dict:
    label = f"obstacle-{index}"
    size_x = between(seed, f"{label}:size-x", 0.45, 0.9)
    size_y = between(seed, f"{label}:size-y", 0.45, 0.9)
    size_z = between(seed, f"{label}:size-z", 0.45, 1.0)
    appear = between(seed, f"{label}:appear", 2.0 + index * 8.0, 6.0 + index * 8.0)
    duration = between(seed, f"{label}:duration", 5.0, 10.0)
    side = -1.0 if sample(seed, f"{label}:side") < 0.5 else 1.0
    return {
        "id": f"{prefix}-box-{index + 1:02d}",
        "position_m": {
            "x": round(side * radius, 3),
            "y": round(size_y / 2.0, 3),
            "z": between(seed, f"{label}:z", -length / 2.0, length / 2.0),
        },
        "size_m": {"x": size_x, "y": size_y, "z": size_z},
        "schedule": {
            "appear_at_s": appear,
            "visible_for_s": duration,
            "disappear_at_s": round(appear + duration, 3),
        },
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for scenario_type, name, length, radius, width, color, count in SCENARIOS:
        seed = scenario_seed(scenario_type, name)
        document = {
            "schema_version": "1.0",
            "metadata": {"name": name, "type": scenario_type, "seed": seed},
            "track": {
                "straight_length_m": length,
                "turn_radius_m": radius,
                "line_width_m": width,
                "background_color_rgb": dict(zip(("r", "g", "b"), color)),
            },
            "obstacles": [
                obstacle(seed, scenario_type, index, length, radius)
                for index in range(count)
            ],
        }
        target = OUTPUT_DIR / f"{name}.json"
        target.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
