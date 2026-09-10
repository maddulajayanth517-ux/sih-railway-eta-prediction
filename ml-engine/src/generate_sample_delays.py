"""Generate clearly synthetic delay labels for local pipeline validation.

This is demo data only. It must not be used as a claim of real-world model
accuracy; replace it with observed railway delay records for production use.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def stable_station_signal(value: str) -> int:
    return sum((index + 1) * ord(char) for index, char in enumerate(value)) % 9


def generate(schedule_path: Path, output_path: Path, seed: int = 42) -> None:
    schedule = pd.read_csv(schedule_path)
    required = {"station_name", "distance_from_origin", "train_no"}
    missing = sorted(required.difference(schedule.columns))
    if missing:
        raise ValueError(f"Schedule is missing columns: {missing}")

    frame = schedule[["station_name", "distance_from_origin", "train_no"]].dropna().copy()
    frame["distance_from_origin"] = pd.to_numeric(frame["distance_from_origin"])
    station_signal = frame["station_name"].astype(str).map(stable_station_signal)
    delay = (
        3.0
        + frame["distance_from_origin"].to_numpy(dtype=float) * 0.08
        + station_signal.to_numpy(dtype=float)
    )
    noise = np.random.default_rng(seed).normal(0.0, 1.0, len(frame))
    frame["delay_minutes"] = np.maximum(0.0, np.rint(delay + noise)).astype(int)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    print(f"Wrote {len(frame)} synthetic labeled rows to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic ETA labels")
    parser.add_argument("--schedule-path", type=Path, required=True)
    parser.add_argument("--output-path", type=Path, required=True)
    args = parser.parse_args()
    generate(args.schedule_path, args.output_path)


if __name__ == "__main__":
    main()