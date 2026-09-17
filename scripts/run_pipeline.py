#!/usr/bin/env python3
"""
Step 4: the combined pipeline. This is the script the eventual GitHub
Actions workflow (Step 6) will run on a schedule. Each run:

  1. Fetches the current season's match list from the InCrowd feed.
  2. Adds any newly-completed matches to the local results ledger
     (scripts/sample_data/results_ledger.json) - this is what keeps the
     Elo ratings current as the season progresses.
  3. (Re)computes the full 5-parameter entertainment score for any match
     that's either new, or was completed recently enough to still be in
     the "correction window" (late data-provider corrections).
  4. Writes the PUBLIC, spoiler-safe output to docs/data/scores.json -
     only match names, dates, and computed 0-100 scores. Nothing in this
     file should ever let a reader infer who won or by how much.

     This lives under docs/ (not a top-level data/) because the site is
     served via GitHub Pages from the /docs folder - anything the
     deployed site needs to fetch at runtime has to live inside it.

Everything this script reads or writes under scripts/sample_data/ is
raw match data (real scores, events) and stays out of git via
.gitignore. Only docs/data/scores.json (and the rest of docs/) is meant
to be committed.

Usage:
    python scripts/run_pipeline.py             # current season (normal scheduled use)
    python scripts/run_pipeline.py 202501      # override season - e.g. backfill a
                                                # completed past season into data/scores.json
"""

import json
import os
import sys
from datetime import datetime, timezone

from feed_client import current_season, fetch_match_list, fetch_match_detail, is_completed
from init_ledger import load_ledger, save_ledger, ledger_key, ensure_ledger_bootstrapped
from build_elo_ratings import build_ratings_before, upset_score_for_match
from scoring_engine import compute_entertainment_score

RECHECK_WINDOW_DAYS = 3  # re-score matches completed this recently, in case of late corrections

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
PUBLIC_OUTPUT_PATH = os.path.join(REPO_ROOT, "docs", "data", "scores.json")


def load_public_output():
    if not os.path.exists(PUBLIC_OUTPUT_PATH):
        return {}
    with open(PUBLIC_OUTPUT_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_public_output(entries: dict):
    os.makedirs(os.path.dirname(PUBLIC_OUTPUT_PATH), exist_ok=True)
    with open(PUBLIC_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, sort_keys=False)


def days_since(date_str: str, now: datetime) -> float:
    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    return (now - dt).total_seconds() / 86400.0


def build_public_entry(match_id, list_item: dict, detail: dict, upset: float) -> dict:
    breakdown = compute_entertainment_score(detail, upset=upset)
    return {
        "match_id": match_id,
        "date": list_item.get("date"),
        "competition": "URC",
        "home_team": list_item["homeTeam"]["name"],
        "away_team": list_item["awayTeam"]["name"],
        "scores": {
            "margin": round(breakdown.margin, 1),
            "momentum": round(breakdown.momentum, 1),
            "clutch": round(breakdown.clutch, 1),
            "scoring_output": round(breakdown.scoring_output, 1),
            "upset": round(breakdown.upset, 1),
            "overall": round(breakdown.overall, 1),
        },
    }


def run():
    added, ledger_total = ensure_ledger_bootstrapped()
    if added:
        print(f"Ledger bootstrap: merged {added} entries from season_results_*.json "
              f"(ledger now has {ledger_total} total).")

    season = sys.argv[1] if len(sys.argv) > 1 else current_season()
    print(f"Fetching match list for season {season}...")
    matches = fetch_match_list(season)
    completed = [m for m in matches if is_completed(m)]
    print(f"  {len(matches)} total matches, {len(completed)} completed.\n")

    ledger = load_ledger()
    known_keys = {ledger_key(e) for e in ledger}
    public_output = load_public_output()

    now = datetime.now(timezone.utc)
    changed = False

    for m in sorted(completed, key=lambda m: m.get("date", "")):
        key = (m["date"], m["homeTeam"]["id"], m["awayTeam"]["id"])
        match_id = str(m["id"])
        is_new_to_ledger = key not in known_keys

        if is_new_to_ledger:
            ledger.append({
                "match_id": m["id"],
                "date": m["date"],
                "home_id": m["homeTeam"]["id"],
                "away_id": m["awayTeam"]["id"],
                "home_score": m["homeTeam"]["score"],
                "away_score": m["awayTeam"]["score"],
            })
            known_keys.add(key)

        # Note: this is deliberately keyed on the PUBLIC output, not the
        # ledger - a match can already be in the ledger (e.g. from a bulk
        # fetch_season_results.py backfill) without ever having been
        # scored into data/scores.json yet.
        not_yet_published = match_id not in public_output
        in_recheck_window = days_since(m["date"], now) <= RECHECK_WINDOW_DAYS
        needs_score_check = not_yet_published or in_recheck_window
        if not needs_score_check:
            continue

        reason = "new" if not_yet_published else "recheck window"
        print(f"Scoring match {match_id} ({m['homeTeam']['name']} vs {m['awayTeam']['name']}, "
              f"{m['date']}) - {reason}...")

        detail = fetch_match_detail(m["id"], season)
        if detail is None:
            print(f"  FAILED to fetch detail for match {match_id}, skipping this run.")
            continue

        ratings = build_ratings_before(m["date"])
        upset = upset_score_for_match(detail, ratings=ratings)
        new_entry = build_public_entry(match_id, m, detail, upset)

        if public_output.get(match_id) != new_entry:
            public_output[match_id] = new_entry
            changed = True
            print(f"  -> overall score {new_entry['scores']['overall']} / 100 (updated)")
        else:
            print("  -> no change from previously published score")

    save_ledger(ledger)

    if changed:
        save_public_output(public_output)
        print(f"\nWrote updates to {PUBLIC_OUTPUT_PATH}")
    else:
        print("\nNo public-facing changes this run - data/scores.json left untouched.")


if __name__ == "__main__":
    run()
