"""
Entertainment-score engine for a single URC match, implementing the
methodology in docs/overview.md ("Excitement Scoring Methodology").

Input: the raw match-detail JSON as returned by the InCrowd Sports feed
(see scripts/test_incrowd_fetch.py) - specifically the `data` object,
i.e. match["homeTeam"], match["awayTeam"], match["events"].

This module only computes numbers; it never decides what's safe to show
publicly. Anything it returns other than the final composite scores
(0-100 per parameter, 0-100 overall) is raw match data and must stay
server-side per the project's zero-spoilers rule.
"""

from dataclasses import dataclass, field
from typing import Optional


# --- Rugby scoring values (event type -> points), matching Rugby-Data ---
SCORING_VALUES = {
    "Try": 5,
    "Penalty Try": 5,
    "Conversion": 2,
    "Penalty": 3,
    "Drop goal": 3,
}
TRY_BUCKET_TYPES = {"Try", "Penalty Try", "Conversion"}
KICK_BUCKET_TYPES = {"Penalty", "Drop goal"}

# --- Margin parameter anchors (also reused by Clutch's margin sub-score) ---
MARGIN_MAX_SCORE_AT = 7    # margin <= this -> 100
MARGIN_ZERO_SCORE_AT = 30  # margin >= this -> 0

# --- Momentum swings diminishing-returns table (also reused by Clutch) ---
MOMENTUM_TABLE = {0: 0, 1: 50, 2: 75, 3: 90}
MOMENTUM_MAX = 100  # 4+

# --- Clutch window and sub-weights ---
CLUTCH_WINDOW_MINUTES = 10
CLUTCH_MARGIN_WEIGHT = 0.4
CLUTCH_MOMENTUM_WEIGHT = 0.6

# --- Final formula weights ---
WEIGHTS = {
    "margin": 0.20,
    "momentum": 0.20,
    "clutch": 0.25,
    "scoring_output": 0.20,
    "upset": 0.15,
}


def margin_score(margin: float) -> float:
    """Piecewise: flat 100 at/under 7, flat 0 at/over 30, linear between."""
    margin = abs(margin)
    if margin <= MARGIN_MAX_SCORE_AT:
        return 100.0
    if margin >= MARGIN_ZERO_SCORE_AT:
        return 0.0
    span = MARGIN_ZERO_SCORE_AT - MARGIN_MAX_SCORE_AT
    return 100.0 * (MARGIN_ZERO_SCORE_AT - margin) / span


def momentum_score(swing_count: int) -> float:
    if swing_count >= 4:
        return float(MOMENTUM_MAX)
    return float(MOMENTUM_TABLE[swing_count])


@dataclass
class ScoringEvent:
    minute: int
    second: int
    team_id: int
    points: int
    bucket: str  # "try" or "kick"


def extract_scoring_events(match: dict) -> list[ScoringEvent]:
    """Pull out only the events that change the score, in feed order
    (the feed's own event order is already chronological; sorting by
    `minute` alone is unsafe because of the Second-Half-Start marker,
    which reports minute=40 even though it follows a First-Half-End
    marker at a later minute due to injury time)."""
    out = []
    for e in match.get("events", []):
        etype = e.get("type")
        if etype not in SCORING_VALUES:
            continue
        bucket = "try" if etype in TRY_BUCKET_TYPES else "kick"
        out.append(ScoringEvent(
            minute=e.get("minute", 0),
            second=e.get("second", 0),
            team_id=e.get("teamId"),
            points=SCORING_VALUES[etype],
            bucket=bucket,
        ))
    return out


def count_momentum_swings(scoring_events: list[ScoringEvent], team_a_id: int, team_b_id: int,
                           minute_min: Optional[int] = None, minute_max: Optional[int] = None) -> int:
    """Replays the scoreline and counts leader-state transitions (A-leads /
    B-leads / tied), excluding the very first score of the match (there's
    no prior leader to change from). If minute_min/minute_max are given,
    the running score is still built from the *entire* match (so we know
    who's ahead entering the window), but only transitions that occur
    within the window are counted - this lets the Clutch parameter ask
    "how many swings happened in the last 10 minutes" without losing
    track of the pre-window score state."""
    score_a, score_b = 0, 0
    leader = None  # None until the first score of the whole match
    swings = 0
    seen_first_score = False

    for ev in scoring_events:
        if ev.team_id == team_a_id:
            score_a += ev.points
        elif ev.team_id == team_b_id:
            score_b += ev.points
        else:
            continue  # shouldn't happen, but don't crash on unknown team ids

        new_leader = "A" if score_a > score_b else ("B" if score_b > score_a else "TIE")

        in_window = (minute_min is None or ev.minute >= minute_min) and \
                    (minute_max is None or ev.minute <= minute_max)

        if not seen_first_score:
            seen_first_score = True
        elif new_leader != leader and in_window:
            swings += 1

        leader = new_leader

    return swings


def scoring_output_score(scoring_events: list[ScoringEvent]) -> float:
    try_points = sum(ev.points for ev in scoring_events if ev.bucket == "try")
    kick_points = sum(ev.points for ev in scoring_events if ev.bucket == "kick")
    total = try_points + kick_points
    if total == 0:
        return 0.0
    return 100.0 * try_points / total


def clutch_score(scoring_events: list[ScoringEvent], team_a_id: int, team_b_id: int,
                  final_margin: float, total_match_minutes: int) -> float:
    window_start = total_match_minutes - CLUTCH_WINDOW_MINUTES
    late_swings = count_momentum_swings(
        scoring_events, team_a_id, team_b_id,
        minute_min=window_start, minute_max=total_match_minutes,
    )
    margin_sub = margin_score(final_margin)
    momentum_sub = momentum_score(late_swings)
    return CLUTCH_MARGIN_WEIGHT * margin_sub + CLUTCH_MOMENTUM_WEIGHT * momentum_sub


@dataclass
class ScoreBreakdown:
    margin: float
    momentum: float
    clutch: float
    scoring_output: float
    upset: float
    overall: float = field(init=False)

    def __post_init__(self):
        self.overall = (
            WEIGHTS["margin"] * self.margin
            + WEIGHTS["momentum"] * self.momentum
            + WEIGHTS["clutch"] * self.clutch
            + WEIGHTS["scoring_output"] * self.scoring_output
            + WEIGHTS["upset"] * self.upset
        )


def compute_entertainment_score(match: dict, upset: float) -> ScoreBreakdown:
    """upset must be supplied by the caller - the Elo system (Step 3)
    isn't built yet, so callers should pass 50 (neutral) as a placeholder
    until it exists."""
    home = match["homeTeam"]
    away = match["awayTeam"]
    team_a_id, team_b_id = home["id"], away["id"]

    scoring_events = extract_scoring_events(match)

    final_margin = abs(home["score"] - away["score"])

    # Sanity-check: does replaying the events reproduce the feed's own
    # final score? If not, our event parsing/scoring values are wrong.
    replay_a = sum(ev.points for ev in scoring_events if ev.team_id == team_a_id)
    replay_b = sum(ev.points for ev in scoring_events if ev.team_id == team_b_id)
    if replay_a != home["score"] or replay_b != away["score"]:
        print(f"WARNING: event replay ({replay_a}-{replay_b}) doesn't match "
              f"feed's final score ({home['score']}-{away['score']}) - "
              f"check for unhandled event types or missing SCORING_VALUES entries.")

    total_minutes = max((e.get("minute", 0) for e in match.get("events", [])), default=80)

    full_swings = count_momentum_swings(scoring_events, team_a_id, team_b_id)

    return ScoreBreakdown(
        margin=margin_score(final_margin),
        momentum=momentum_score(full_swings),
        clutch=clutch_score(scoring_events, team_a_id, team_b_id, final_margin, total_minutes),
        scoring_output=scoring_output_score(scoring_events),
        upset=upset,
    )
