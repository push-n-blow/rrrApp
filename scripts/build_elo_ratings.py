"""
Builds Elo ratings (scripts/elo.py) by replaying scripts/sample_data/
results_ledger.json (see init_ledger.py / run_pipeline.py) in
chronological order, applying season-boundary regression whenever the
replay crosses from one URC season into the next.
"""

import json
import os
from datetime import datetime

from elo import EloRatings

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR = os.path.join(SCRIPT_DIR, "sample_data")
LEDGER_PATH = os.path.join(SAMPLE_DIR, "results_ledger.json")


def season_of(date_str: str) -> str:
    """Same rule as feed_client.current_season(), applied to a specific
    match date rather than "now" - URC seasons run August-June."""
    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    start_year = dt.year if dt.month >= 8 else dt.year - 1
    return f"{start_year}01"


def _load_ledger():
    if not os.path.exists(LEDGER_PATH):
        return []
    with open(LEDGER_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_ratings_before(target_date: str = None) -> EloRatings:
    """Replay the ledger in chronological order, stopping strictly
    before target_date (ISO 8601 string) if given. Pass None to replay
    everything available."""
    matches = sorted(_load_ledger(), key=lambda m: m["date"])
    r = EloRatings()
    current_season_code = None

    for m in matches:
        if target_date is not None and m["date"] >= target_date:
            break

        season_code = season_of(m["date"])
        if current_season_code is not None and season_code != current_season_code:
            r.new_season()
        current_season_code = season_code

        r.record_result(m["home_id"], m["away_id"], m["home_score"], m["away_score"])

    return r


def upset_score_for_match(match: dict, ratings: EloRatings = None) -> float:
    """Given a full match-detail dict (as fetched by test_incrowd_fetch.py
    / run_pipeline.py) and, optionally, pre-built ratings, returns the
    Upset/Favorite score for that match. If ratings isn't given, builds
    them from the ledger up to (not including) this match's own date."""
    if ratings is None:
        ratings = build_ratings_before(match["date"])

    home_id = match["homeTeam"]["id"]
    away_id = match["awayTeam"]["id"]
    winner_id = match.get("matchWinner")
    if winner_id is None:
        home_score, away_score = match["homeTeam"]["score"], match["awayTeam"]["score"]
        winner_id = home_id if home_score > away_score else (away_id if away_score > home_score else None)

    return ratings.upset_score(home_id, away_id, winner_id)


if __name__ == "__main__":
    ratings = build_ratings_before()
    print(f"Teams tracked: {len(ratings.ratings)}")
    print("\nCurrent ratings (highest first):")
    for team_id, rating in sorted(ratings.ratings.items(), key=lambda kv: -kv[1]):
        print(f"  team {team_id}: {rating:.1f}")
