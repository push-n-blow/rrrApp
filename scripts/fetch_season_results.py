#!/usr/bin/env python3
"""
Step 3 support script: fetch compact historical match RESULTS (team ids,
scores, date) for one or more URC seasons, to seed the Elo rating system
(scripts/elo.py).

Output: scripts/sample_data/season_results_<season>.json - a compact
list of {date, home_id, away_id, home_score, away_score}. This is raw
result data (spoilers), so it's gitignored, same as the single-match
samples from test_incrowd_fetch.py.

Usage:
    python scripts/fetch_season_results.py 202301 202401 202501
    (space-separated list of seasons in YYYY01 format; processes oldest
    first, which is the order the Elo system needs to replay them in)
"""

import json
import os
import sys
import time

from feed_client import fetch_match_list, fetch_match_detail, is_completed

POLITE_DELAY = 0.75  # seconds between detail requests, if we need them

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR = os.path.join(SCRIPT_DIR, "sample_data")


def fetch_season(season: str):
    print(f"Fetching match list for season {season}...")
    matches = fetch_match_list(season)
    completed = [m for m in matches if is_completed(m)]
    print(f"  {len(matches)} total matches, {len(completed)} completed.")

    if not completed:
        return []

    sample = completed[0]
    home_score = sample.get("homeTeam", {}).get("score")
    away_score = sample.get("awayTeam", {}).get("score")
    has_list_scores = home_score is not None and away_score is not None
    print(f"  List items include scores directly: {has_list_scores}")

    results = []
    if has_list_scores:
        for m in completed:
            results.append({
                "date": m.get("date"),
                "home_id": m["homeTeam"]["id"],
                "away_id": m["awayTeam"]["id"],
                "home_score": m["homeTeam"]["score"],
                "away_score": m["awayTeam"]["score"],
            })
    else:
        print(f"  Falling back to per-match detail fetches for {len(completed)} matches "
              f"(this will take a couple of minutes, ~{POLITE_DELAY}s delay between requests)...")
        for i, m in enumerate(completed, 1):
            detail = fetch_match_detail(m["id"], season)
            if detail is None:
                print(f"  [{i}/{len(completed)}] FAILED match {m['id']}, skipping.")
                continue
            results.append({
                "date": detail.get("date"),
                "home_id": detail["homeTeam"]["id"],
                "away_id": detail["awayTeam"]["id"],
                "home_score": detail["homeTeam"]["score"],
                "away_score": detail["awayTeam"]["score"],
            })
            if i % 10 == 0:
                print(f"  [{i}/{len(completed)}] done...")
            time.sleep(POLITE_DELAY)

    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/fetch_season_results.py <season1> [season2] ...")
        print("       e.g. python scripts/fetch_season_results.py 202301 202401 202501")
        sys.exit(1)

    os.makedirs(SAMPLE_DIR, exist_ok=True)

    for season in sys.argv[1:]:
        results = fetch_season(season)
        results.sort(key=lambda r: r.get("date") or "")
        out_path = os.path.join(SAMPLE_DIR, f"season_results_{season}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"  Wrote {len(results)} results to {out_path}\n")


if __name__ == "__main__":
    main()
