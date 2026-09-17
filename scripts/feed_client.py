"""
Shared InCrowd Sports feed client - the request pattern validated in
Step 1 (see docs/overview.md, Confirmed Data Schema), factored out so
test_incrowd_fetch.py, fetch_season_results.py, and run_pipeline.py
don't each carry their own copy.
"""

import time
from datetime import datetime, timezone

import requests

COMP_ID = 1068          # URC
PROVIDER = "rugbyviz"
BASE_URL = "https://rugby-union-feeds.incrowdsports.com/v1/matches"
TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds, exponential backoff

# Confirmed empirically (2026-09): completed URC matches report "result".
# Kept as a set (not a single value) since this may vary by competition/
# provider and the reference project (Rugby-Data) uses a broader list.
COMPLETED_STATUSES = {"result", "complete", "completed", "finished", "fulltime", "ft", "played"}


def current_season() -> str:
    """Season start year as 'YYYY01' (URC season runs Aug-Jun)."""
    now = datetime.now(timezone.utc)
    start_year = now.year if now.month >= 8 else now.year - 1
    return f"{start_year}01"


def fetch_with_retry(url: str):
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  Retry {attempt + 1}/{MAX_RETRIES - 1} after error: {e}")
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                print(f"  Failed after {MAX_RETRIES} attempts: {e}")
                return None
    return None


def fetch_match_list(season: str):
    """Returns the raw list of match dicts for a season, or [] on failure."""
    url = f"{BASE_URL}?compId={COMP_ID}&season={season}&provider={PROVIDER}"
    resp = fetch_with_retry(url)
    if resp is None:
        return []
    return resp.json().get("data", [])


def fetch_match_detail(match_id, season: str):
    """Returns the full match-detail dict for one match, or None on failure."""
    url = f"{BASE_URL}/{match_id}?season={season}&provider={PROVIDER}"
    resp = fetch_with_retry(url)
    if resp is None:
        return None
    return resp.json().get("data", {})


def is_completed(match: dict) -> bool:
    return (match.get("status") or "").lower() in COMPLETED_STATUSES
