# RRRApp!
Rugby Recap Recommendation App

## About

A static website that helps you decide which recent rugby match is worth watching in replay (as of now URC only) — without ever revealing scores, results, or who won. Inspired by wikihoops, replayrank and alike (see Alternatives at the bottom of the page).

Built by: Claude Code\
Language: Python\
Hosting: github pages (https://push-n-blow.github.io/rrrApp/)

### Rugby\-specific alternative

I found only one website that tries to do it for rugby specifically -- [WatchIt Rugby](https://watchit.eloxia.fr/).
The games are rated by humans and you need to login to rate. Not very popular, not enough votes to get fair results. See this reddit post with explanations from the author -- https://www.reddit.com/r/rugbyunion/comments/1nfegs1/i_built_a_site_to_rate_rugby_matches_so_you_know/

## How it works

All details see here: `spec/overview.md` (doc is created by Claude, I didn't clean it up really well, so might be a bit bloated)

In short, for game data I used the InCrowd Sports feed documented by the open\-source project [transientlunatic/Rugby\-Data](https://github.com/transientlunatic/Rugby-Data).

The entertainment score is built from five parameters, each computed on a 0–100 scale, then combined into one final 0–100 score via a weighted formula.

`Entertainment Score = 0.20 × Margin + 0.20 × Momentum + 0.25 × Clutch + 0.20 × ScoringOutput + 0.15 × Upset`

All parameters are designed to be computable from the InCrowd Sports feed.

### 1. Margin
```
score = 100                                  if margin <= 7
score = 0                                    if margin >= 30
score = 100 × (30 − margin) / (30 − 7)       otherwise
```
### 2. Momentum

| Momentum swings / number of lead changes | Score |
| --- | --- |
| 0 | 0 |
| 1 | 50 |
| 2 | 75 |
| 3 | 90 |
| 4+ | 100 |

Equivalent to roughly `100 × (1 − 0.5^N)`

### 3. Scoring Output (Tries vs. Kicks)

The share of total match points scored via tries: `(try + conversion points) / total match points`.
Mapped linearly: 0% tries\-share → 0, 100% → 100.

### 4. Clutch

Looks specifically at the final **10 minutes** of the match, combining two sub\-scores:

- **Margin sub\-score:** the final full\-time margin, using the same 7/30 scale as parameter 1.
- **Momentum sub\-score:** momentum swings (lead changes/ties) occurring *only* within the last 10 minutes, using the same diminishing\-returns curve as parameter 2. The 10\-minute window is measured back from the match's actual final minute (the `End` event, which can be past 80 with injury time), not a hardcoded 80.

The two are combined as `Clutch = 0.4 × MarginSubScore + 0.6 × MomentumSubScore` — momentum weighted higher than margin (since "something happened" late is more memorable than "it merely stayed close").

### 5. Upset

Elo rating system maintained internally. This part was suggested by Claude, I am yet to figure out how it works. Starting ratings were calculated based on last five (iirc) seasons. See `spec/overview.md` for more context.

`UpsetScore = 100 × (1 − winProbabilityOfActualWinner)`.

## Alternatives

| App | Sports covered | Scoring approach |
| --- | --- | --- |
| [Wikihoops](https://wikihoops.com/) | NBA, WNBA only | 1\-10 scale: algorithmic score from game/player stats (self\-described as "quite rudimental") \+ crowd\-sourced upvote/downvote score (7\-day voting window) |
| [ReplayRank](https://replayrank.com/) | NBA only | "Excitement Score" (0\-100) built from lead changes, scoring volatility, clutch possessions, overtime drama, star performances, and end\-game pressure. Notably lets users customize the score themselves via toggles for closeness, volatility, offensive flow, player impact, and late\-game drama; also offers tag\-based filtering (e.g. #DownToTheWire), team pages, and an "Excitement vs Wins" comparison view. One of the more transparent and feature\-rich methodologies found. |
| [HideScore](https://hidescore.com/) | NBA, NFL, NHL, MLB, MLS, major soccer leagues, golf, cricket, World Cup | "Competitiveness rating" — flags whether a match was close or a blowout, without revealing the result |
| [SportsRec](https://sportsrec.app/) | NCAA/NBA/WNBA basketball, NFL/college football, soccer competitions, tennis, MLB | 0\-100 score combining "Importance" (pre\-game stakes) \+ "Excitement" (in\-game drama), bucketed into tiers (Must\-Watch 78\+, Interesting 55\+); soccer uses a separate model factoring qualification/relegation odds |
| [skore.info](https://skore.info/) | Soccer, NBA, MLB, NHL, NFL | Filters replays "by excitement level"; methodology not published. Has a short part on alternative  |
| [Spoiler Free Scores](https://spoilerfreescores.com/) | Soccer, Cricket, American top leagues | I idn't search really well|

## Credits

The work on this project is inspired by The Vibe Coding Studio and Code 4 Lovers educational programs by Phillip Compeau -- https://www.philomathlearning.com/