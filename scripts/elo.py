"""
Elo rating system for URC teams, feeding the "Upset / Favorite" parameter
of the entertainment score (see docs/overview.md, section 5).

Design (v1 defaults - tunable, see constants below):
- Baseline rating 1500 for a team with no history.
- Home advantage: added to the home team's rating only for the purposes
  of computing win probability / margin-of-victory scaling - it is NOT
  permanently added to the stored rating.
- K-factor: 20 (moderate - rugby has higher scoring variance than e.g.
  soccer, so ratings shouldn't swing as hard per match as a lower-scoring
  sport's Elo would).
- Margin-of-victory multiplier: adapted from FiveThirtyEight's NFL Elo
  model - a big win over a weaker team barely moves the rating (already
  expected), while a big win over a stronger team moves it more (genuine
  signal). Optional; can be disabled.
- Season carryover with mild regression to the mean (25% back toward
  1500 at the start of each season), to account for typical squad
  turnover without fully discarding a team's history. This isn't yet
  written into the spec doc - flagging for confirmation before treating
  it as final.

This module only maintains ratings and computes the Upset score for a
single match; it doesn't fetch data itself (see fetch_season_results.py).
"""

import math
from dataclasses import dataclass, field


BASELINE_RATING = 1500.0
HOME_ADVANTAGE = 65.0     # Elo points, added to home team for prob/MOV calc only
K_FACTOR = 20.0
SEASON_REGRESSION = 0.25  # fraction reverted toward baseline at each new season


def expected_score(rating_a: float, rating_b: float) -> float:
    """Standard Elo win probability for A vs B."""
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def mov_multiplier(margin: int, winner_rating: float, loser_rating: float) -> float:
    """FiveThirtyEight-style margin-of-victory multiplier: rewards upsets
    more than expected blowouts, and has diminishing returns on margin
    itself (ln, not linear)."""
    rating_diff = winner_rating - loser_rating
    return math.log(margin + 1) * (2.2 / (0.001 * rating_diff + 2.2))


@dataclass
class EloRatings:
    ratings: dict = field(default_factory=dict)

    def get(self, team_id: int) -> float:
        return self.ratings.get(team_id, BASELINE_RATING)

    def new_season(self):
        """Call once between seasons: regress every known team partway
        back toward the baseline, rather than wiping history entirely."""
        for team_id, rating in self.ratings.items():
            self.ratings[team_id] = rating + SEASON_REGRESSION * (BASELINE_RATING - rating)

    def record_result(self, home_id: int, away_id: int, home_score: int, away_score: int,
                       use_mov: bool = True):
        """Update both teams' ratings after a completed match. Drawn
        matches (rugby allows draws) are handled as a 0.5/0.5 result
        with no margin-of-victory scaling."""
        home_rating = self.get(home_id)
        away_rating = self.get(away_id)

        home_effective = home_rating + HOME_ADVANTAGE
        expected_home = expected_score(home_effective, away_rating)

        if home_score > away_score:
            actual_home = 1.0
        elif home_score < away_score:
            actual_home = 0.0
        else:
            actual_home = 0.5

        k = K_FACTOR
        if use_mov and home_score != away_score:
            margin = abs(home_score - away_score)
            winner_rating = home_effective if home_score > away_score else away_rating
            loser_rating = away_rating if home_score > away_score else home_effective
            k *= mov_multiplier(margin, winner_rating, loser_rating)

        delta = k * (actual_home - expected_home)
        self.ratings[home_id] = home_rating + delta
        self.ratings[away_id] = away_rating - delta

    def upset_score(self, home_id: int, away_id: int, winner_id: int) -> float:
        """0-100: how unlikely the actual winner was to win, based on
        ratings as they stood BEFORE this match (call this before
        record_result for the same match). A heavy favorite winning as
        expected scores low; a genuine upset scores high. A draw is
        scored as "how close to a 50/50 tossup this was," which isn't
        quite the same question - flagged as an open edge case."""
        home_rating = self.get(home_id) + HOME_ADVANTAGE
        away_rating = self.get(away_id)
        prob_home = expected_score(home_rating, away_rating)

        if winner_id == home_id:
            win_prob = prob_home
        elif winner_id == away_id:
            win_prob = 1.0 - prob_home
        else:
            # draw: score based on how far the pre-match probabilities
            # were from an even 50/50 split
            win_prob = 0.5 + abs(prob_home - 0.5)

        return 100.0 * (1.0 - win_prob)
