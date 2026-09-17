#!/usr/bin/env python3
"""
One-time (and re-runnable) migration: merge every scripts/sample_data/
season_results_<season>.json file (from fetch_season_results.py) into a
single chronological ledger, scripts/sample_data/results_ledger.json,
which is what build_elo_ratings.py and run_pipeline.py read from going
forward.

Safe to re-run: entries are deduped by (date, home_id, away_id).

Usage:
    python scripts/init_ledger.py
"""

import glob
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR = os.path.join(SCRIPT_DIR, "sample_data")
LEDGER_PATH = os.path.join(SAMPLE_DIR, "results_ledger.json")


def ledger_key(entry):
    return (entry["date"], entry["home_id"], entry["away_id"])


def load_ledger():
    if not os.path.exists(LEDGER_PATH):
        return []
    with open(LEDGER_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_ledger(entries):
    entries = sorted(entries, key=lambda e: e["date"])
    with open(LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


def ensure_ledger_bootstrapped():
    """Called by run_pipeline.py at startup - merges any season_results_*.json
    files found into the ledger (a no-op if there aren't any, or if
    everything in them is already merged in)."""
    ledger = load_ledger()
    known_keys = {ledger_key(e) for e in ledger}

    added = 0
    for path in sorted(glob.glob(os.path.join(SAMPLE_DIR, "season_results_*.json"))):
        with open(path, encoding="utf-8") as f:
            season_entries = json.load(f)
        for e in season_entries:
            key = ledger_key(e)
            if key not in known_keys:
                ledger.append({
                    "match_id": e.get("match_id"),
                    "date": e["date"],
                    "home_id": e["home_id"],
                    "away_id": e["away_id"],
                    "home_score": e["home_score"],
                    "away_score": e["away_score"],
                })
                known_keys.add(key)
                added += 1

    if added:
        save_ledger(ledger)
    return added, len(ledger)


if __name__ == "__main__":
    added, total = ensure_ledger_bootstrapped()
    print(f"Added {added} new entries; ledger now has {total} total results.")
    print(f"Ledger: {LEDGER_PATH}")
