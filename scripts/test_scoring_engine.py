#!/usr/bin/env python3
"""
Full pipeline test: run the scoring engine (scoring_engine.py) against a
real match sample fetched by test_incrowd_fetch.py, using a real
Elo-based Upset score (build_elo_ratings.py, seeded via init_ledger.py)
when historical results are available in scripts/sample_data/, falling
back to a neutral placeholder (50) otherwise.

Usage:
    python scripts/test_scoring_engine.py scripts/sample_data/match_288005.json
"""
import json
import os
import sys

from scoring_engine import compute_entertainment_score, extract_scoring_events
from build_elo_ratings import upset_score_for_match, LEDGER_PATH
from init_ledger import ensure_ledger_bootstrapped


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_scoring_engine.py <path-to-sample-match.json>")
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8") as f:
        match = json.load(f)

    events = extract_scoring_events(match)
    print(f"Parsed {len(events)} scoring events "
          f"({sum(1 for e in events if e.bucket == 'try')} try-bucket, "
          f"{sum(1 for e in events if e.bucket == 'kick')} kick-bucket)\n")

    # Make sure any already-fetched season_results_*.json files are folded
    # into the ledger, so this works standalone even if run_pipeline.py
    # (which also does this) hasn't been run yet.
    added, ledger_total = ensure_ledger_bootstrapped()
    if added:
        print(f"Ledger bootstrap: merged {added} entries from season_results_*.json "
              f"(ledger now has {ledger_total} total).\n")

    if os.path.exists(LEDGER_PATH):
        upset = upset_score_for_match(match)
        upset_note = "from Elo ratings built off the results ledger"
    else:
        upset = 50.0
        upset_note = "placeholder - run fetch_season_results.py to seed real Elo ratings"

    breakdown = compute_entertainment_score(match, upset=upset)

    print("Per-parameter scores (0-100):")
    print(f"  Margin:          {breakdown.margin:6.1f}")
    print(f"  Momentum:        {breakdown.momentum:6.1f}")
    print(f"  Clutch:          {breakdown.clutch:6.1f}")
    print(f"  Scoring Output:  {breakdown.scoring_output:6.1f}")
    print(f"  Upset:           {breakdown.upset:6.1f}  ({upset_note})")
    print()
    print(f"Overall entertainment score: {breakdown.overall:.1f} / 100")


if __name__ == "__main__":
    main()
