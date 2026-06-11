"""
seeds/make_schedule.py — Generate the frozen episode seed schedule (PROTOCOL.md D2).

Each episode: 6 REAL + 3 GHOST + 1 FRAUD posting, order randomized.
Deterministic from MASTER_SEED. Commit the resulting schedule.json BEFORE runs.

Run: python seeds/make_schedule.py --episodes 360
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

MASTER_SEED = 73411  # frozen
COMPOSITION = {"REAL": 6, "GHOST": 3, "FRAUD": 1}

BASE = Path(__file__).resolve().parent.parent
POSTINGS_DIR = BASE / "data" / "postings"
OUT = Path(__file__).resolve().parent / "schedule.json"


def load_ids_by_class() -> dict[str, list[str]]:
    by_class: dict[str, list[str]] = {"REAL": [], "GHOST": [], "FRAUD": []}
    for f in sorted(POSTINGS_DIR.glob("**/*.json")):
        rec = json.loads(f.read_text())
        if rec.get("class_label") in by_class:
            by_class[rec["class_label"]].append(rec["id"])
    return by_class


def main(episodes: int) -> None:
    rng = random.Random(MASTER_SEED)
    by_class = load_ids_by_class()
    for cls, need in COMPOSITION.items():
        if len(by_class[cls]) < need:
            raise SystemExit(f"Not enough {cls} postings ({len(by_class[cls])} < {need}).")

    schedule = {}
    for e in range(episodes):
        ids = []
        for cls, count in COMPOSITION.items():
            ids += rng.sample(by_class[cls], count)
        order = list(range(len(ids)))
        rng.shuffle(order)
        schedule[str(e)] = {"posting_ids": ids, "order_perm": order, "seed_episode": e}

    OUT.write_text(json.dumps(schedule, indent=1))
    print(f"Wrote {episodes} episodes to {OUT} (master seed {MASTER_SEED}).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=360)
    main(ap.parse_args().episodes)
