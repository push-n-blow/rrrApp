#!/usr/bin/env python3
"""
Step 1 validation script: test whether the InCrowd Sports feed
(rugby-union-feeds.incrowdsports.com) actually works the way
transientlunatic/Rugby-Data documents it, for URC (compId=1068).

Run this yourself and share the output - Claude's own tools can't
fetch this domain directly, since its robots.txt disallows automated
fetching and Claude doesn't route around that.

IMPORTANT - this writes a full raw match detail (real score, scorers,
cards, minute-by-minute events) to scripts/sample_data/. That's spoiler
content for a real match, so scripts/sample_data/ should be gitignored
and NEVER committed to the (eventually public) repo. This script and
its .gitignore entry are safe to commit; the JSON files it produces
are not.

Usage:
    pip install requests
    python scripts/test_incrowd_fetch.py             # current season
    python scripts/test_incrowd_fetch.py 202501      # override season (e.g. last season, to find completed matches)
"""

import json
import os
import sys

from feed_client import current_season, fetch_match_list, fetch_match_detail, is_completed

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR = os.path.join(SCRIPT_DIR, "sample_data")


def ensure_gitignore_covers_sample_data():
    """Make sure scripts/sample_data/ is gitignored before we write spoiler data into it."""
    repo_root = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
    gitignore_path = os.path.join(repo_root, ".gitignore")
    entry = "scripts/sample_data/"

    existing = ""
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as f:
            existing = f.read()

    if entry in existing:
        return

    print(f"NOTE: adding '{entry}' to .gitignore (this sample data contains real match "
          f"results/scorers and must never be committed to the repo).")
    with open(gitignore_path, "a", encoding="utf-8") as f:
        if existing and not existing.endswith("\n"):
            f.write("\n")
        f.write(f"\n# Raw match samples fetched for local dev - contains real scores/events (spoilers).\n{entry}\n")


def main():
    ensure_gitignore_covers_sample_data()

    season = sys.argv[1] if len(sys.argv) > 1 else current_season()

    print(f"Fetching match list for season {season}...\n")
    matches = fetch_match_list(season)
    if not matches:
        print("FAILED or no matches returned - nothing further to check.")
        sys.exit(1)

    print(f"OK: got {len(matches)} matches for season {season}.\n")

    matches_sorted = sorted(matches, key=lambda m: m.get("date", ""))
    print("Last 5 matches in the response:")
    for m in matches_sorted[-5:]:
        home = m.get("homeTeam", {}).get("name")
        away = m.get("awayTeam", {}).get("name")
        status = m.get("status")
        print(f"  {m.get('date')}  {home} vs {away}  [status={status}]")

    completed = [m for m in matches_sorted if is_completed(m)]
    if not completed:
        print("\nNo completed matches found this season yet - can't test the detail endpoint.")
        return

    last_completed = completed[-1]
    match_id = last_completed["id"]

    print(f"\nFetching detail for match {match_id} "
          f"({last_completed['homeTeam']['name']} vs {last_completed['awayTeam']['name']})...\n")

    detail = fetch_match_detail(match_id, season)
    if detail is None:
        print("FAILED: could not fetch match detail.")
        sys.exit(1)

    events = detail.get("events", [])
    print(f"OK: match detail has {len(events)} events.")

    if events:
        print("\nAll events:")
        for e in events:
            print(f"  minute={e.get('minute')} type={e.get('type')} teamId={e.get('teamId')} playerId={e.get('playerId')}")
    else:
        print("No events found in the detail response - this would be a problem for our scoring formula.")
        return

    os.makedirs(SAMPLE_DIR, exist_ok=True)
    out_path = os.path.join(SAMPLE_DIR, f"match_{match_id}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(detail, f, indent=2)

    print(f"\nFull raw match detail written to: {out_path}")
    print("(gitignored - this file has the real score/scorers in it, don't commit it)")


if __name__ == "__main__":
    main()
