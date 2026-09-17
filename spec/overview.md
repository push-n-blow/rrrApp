# App Overview

**Repo layout (2026\-09):** this spec lives in `spec/overview.md`. `docs/` is the published site itself (served via GitHub Pages, Settings → Pages → branch `main` / folder `/docs`) — `docs/index.html`, `docs/style.css`, `docs/app.js`, and the pipeline's public output at `docs/data/scores.json`. `scripts/` holds the backend pipeline (`run_pipeline.py` and friends) and its gitignored raw match data (`scripts/sample_data/`). This moved `overview.md` out of `docs/` specifically because Pages only serves what's inside that folder, and a `/docs`\-rooted site can't also hold the spec without publishing it as a page.

## App Idea

A static website that helps you decide which recent rugby match (now only United Rugby Championship, URC) is worth watching in replay — without ever revealing scores, results, or who won.

## Existing Alternatives

A survey of spoiler\-free sports platforms, to understand existing scoring approaches and confirm there's no direct rugby\-focused competitor.

### General / multi\-sport spoiler\-free platforms

| App | Sports covered | Scoring approach |
| --- | --- | --- |
| [Wikihoops](https://wikihoops.com/) | NBA, WNBA only | 1\-10 scale: algorithmic score from game/player stats (self\-described as "quite rudimental") \+ crowd\-sourced upvote/downvote score (7\-day voting window) |
| [ReplayRank](https://replayrank.com/) | NBA only | "Excitement Score" (0\-100) built from lead changes, scoring volatility, clutch possessions, overtime drama, star performances, and end\-game pressure. Notably lets users customize the score themselves via toggles for closeness, volatility, offensive flow, player impact, and late\-game drama; also offers tag\-based filtering (e.g. #DownToTheWire), team pages, and an "Excitement vs Wins" comparison view. One of the more transparent and feature\-rich methodologies found. |
| [HideScore](https://hidescore.com/) | NBA, NFL, NHL, MLB, MLS, major soccer leagues, golf, cricket, World Cup | "Competitiveness rating" — flags whether a match was close or a blowout, without revealing the result |
| [SportsRec](https://sportsrec.app/) | NCAA/NBA/WNBA basketball, NFL/college football, soccer competitions, tennis, MLB | 0\-100 score combining "Importance" (pre\-game stakes) \+ "Excitement" (in\-game drama), bucketed into tiers (Must\-Watch 78\+, Interesting 55\+); soccer uses a separate model factoring qualification/relegation odds |
| [Sports Is Cinema](https://www.barchart.com/story/news/2450042/sportsiscinema-com-launches-ai-powered-spoiler-free-replay-sports-platform-with-dedicated-fifa-world-cup-2026-hub) | Football, cricket, basketball, tennis, baseball, boxing, wrestling, volleyball, motorsport | AI\-powered spoiler masking; no published scoring methodology found; has a "Surprise Me" random\-match feature |
| [skore.info](https://skore.info/) | Soccer, NBA, MLB, NHL, (American) football | Filters replays "by excitement level"; methodology not published |
| [Spoiler Free Scores](https://spoilerfreescores.com/) | Unconfirmed — site was in an error/loading state at time of review; may lean more toward video games than sports | Unconfirmed |
| [NoSpoilerz](http://nospoilerz.com/) | Unconfirmed — page could not be fetched (redirect loop) | Unconfirmed |
| [DTMTS ("Don't Tell Me The Score")](https://www.dtmts.com/) | NBA, NFL, NHL, MLB | Not published |

### Rugby\-specific

| App | Notes |
| --- | --- |
| [WatchIt Rugby](https://watchit.eloxia.fr/top-matches) | Independent project (creator posted to r/rugbyunion). Appears to be the only rugby\-specific spoiler\-free match\-rating site found. Scoring methodology and competition coverage not yet confirmed — site blocks automated fetching (robots.txt) and the announcement is on Reddit (also blocked); worth reviewing manually. |

**Takeaway:** No mainstream spoiler\-free platform covers rugby — HideScore, SportsRec, Sports Is Cinema, skore.info, and now ReplayRank all explicitly omit it (ReplayRank is NBA\-only). WatchIt Rugby is the one rugby\-specific precedent found and is worth studying directly. Of the transparent\-methodology apps, HideScore's competitiveness rating, SportsRec's Importance\+Excitement composite, and ReplayRank's customizable multi\-factor "Excitement Score" are the most useful references for designing our own scoring formula — ReplayRank in particular is a good model for how to break a single score into inspectable sub\-factors.

## Data Sources

Options for getting URC schedule and match data, ranging from "just the fixture list" to "full match detail needed to compute an entertainment score."

### Schedule\-only (spoiler\-safe by construction)

| Source | What it gives | Notes |
| --- | --- | --- |
| [Rugby Fixture — URC calendar](https://www.rugbyfixture.com/league/urc) | iCal feed: `webcal://data.rugbyfixture.io/ical/v1/urc.ics` — date, teams, kickoff time | No scores at all since it's a calendar feed; auto\-updates on reschedules; team\-specific feeds also available. Good for populating "what's on," not for scoring. |

### Detailed match data (needed to compute the entertainment score)

| Source | Access | Coverage / data | Notes |
| --- | --- | --- | --- |
| InCrowd Sports feed (`rugby-union-feeds.incrowdsports.com`) | No API key, undocumented/unofficial | `compId=1068` for URC; `/v1/matches` (list) and `/v1/matches/{id}` (full detail: lineups, scoring events, substitutions, team stats) | Documented by the open\-source project [transientlunatic/Rugby\-Data](https://github.com/transientlunatic/Rugby-Data) (see its [AUTOMATION.md](https://github.com/transientlunatic/Rugby-Data/blob/master/AUTOMATION.md)), which runs a weekly GitHub Action against this feed and appears to be the same backend powering the official [URC Match Centre](https://stats.unitedrugby.com/). **Validated empirically** (2026\-09) via `scripts/test_incrowd_fetch.py` — see Confirmed Data Schema below. Still not an officially published API — check InCrowd Sports' terms before relying on it in production. The repo's own `json/` folder could also be pulled from directly if its data stays current. |
| [API\-Sports Rugby API](https://api-sports.io/documentation/rugby/v1) | Paid, documented | Confirms URC coverage; schedule, historical data, standings across 144 rugby competitions | Free tier: 100 requests/day. Paid: $15/mo (7,500 req/day) up to $35/mo (150,000 req/day). Not currently in use — the InCrowd feed covers everything needed so far. |
| [SportDevs Rugby API](https://sportdevs.com/rugby) | Freemium, documented | Free tier: 300 req/day, "10 major leagues" — URC inclusion not explicitly confirmed | Needs a closer look to confirm URC is in scope. |
| [TheSportsDB](https://www.thesportsdb.com/league/4446-united-rugby-championship) | Free API | Has a dedicated URC league page | Rate limits and whether scores ship separately from fixtures weren't confirmed from available docs. |

### Confirmed Data Schema (validated 2026\-09, InCrowd feed)

Fetched live against a real completed URC match (season `202501`, match id `288005`) to confirm the shape of the data the scoring engine depends on. Match list items carry a `status` field; completed matches report `status: "result"` (not `"finished"`/`"complete"` as the reference project's status list assumes — worth double\-checking each season, since this could be provider\- or competition\-specific).

Each match detail response includes:

- `homeTeam` / `awayTeam`: `id`, `name`, `score` (final), `halfTimeScore`, `eightyMinScore`, and a `stats` block with match\-level aggregates (`tries`, `conversionGoals`, `penaltyGoals`, `dropGoalsConverted`, `penaltyTries`, `yellowCards`, `redCards`, `possession`, `territory`, and dozens more) — useful as a cross\-check against event\-derived totals.
- `events[]`: chronologically ordered, each with `minute`, `second`, `type`, `teamId`, `playerId`. Confirmed event types relevant to scoring: `Try`, `Penalty Try` (not seen yet but expected), `Conversion`, `Missed conversion`, `Penalty`, `Drop goal` (not seen yet but expected), plus non\-scoring markers `First Half Start/End`, `Second Half Start/End`, `End`, `Yellow card`, `Sub On`/`Sub Off`.
- Event minutes run on rugby's continuous 0–80\+ clock (second\-half events are minutes 40–80\+, not reset to 0), **except** the `Second Half Start` marker itself, which reports `minute: 40` even when the `First Half End` marker landed later due to first\-half stoppage time. This makes sorting events by `minute` unsafe — the feed's own array order is already correct chronological order and should be used directly instead.
- Match length isn't fixed at 80: the `End` marker's minute (e.g. 81) should be used as the reference point for "last 10 minutes," not a hardcoded 80.

**Spoiler handling for this raw data:** a fetched match detail (or any `sample_data/` file used for local development) contains the actual score, scorers, and winner, so it must never be committed to the repo. `scripts/test_incrowd_fetch.py` writes samples to `scripts/sample_data/`, which is `.gitignore`d for exactly this reason.

### Scraping (fallback, not preferred)

Sites like the official [URC Match Centre](https://stats.unitedrugby.com/), [All.Rugby](https://all.rugby/tournament/urc/fixtures-results), and [RugbyPass](https://www.rugbypass.com/united-rugby-championship/fixtures-results/) could be scraped directly, but the Match Centre is a client\-side JS app (would need a headless browser), and HTML scraping in general is fragile (selector breakage, ToS risk, no structured guarantees). Only worth falling back to if none of the API options pan out.

### Architectural note

Given the zero\-spoilers requirement, schedule data and match\-result data likely need to be treated as two different trust levels: a spoiler\-safe fixture source (e.g. the iCal feed) can be used anywhere, including client\-side, while detailed match/result data (scores, tries, events) should be fetched and processed only on the backend to compute the entertainment score — the raw result data itself should never be exposed to the frontend, only the derived score.

## Excitement Scoring Methodology

The entertainment score is built from five parameters, each computed on a 0–100 scale, then combined into one final 0–100 score via a weighted formula. All parameters are designed to be computable from the InCrowd Sports feed's chronological match\-events log (see Data Sources) — specifically, the running scoreline reconstructed from timestamped scoring events.

### 1. Margin

The final full\-time score margin. A margin of **7 points or fewer** (rugby's own "one\-score game" — the threshold URC's own bonus\-point rules use to define a close loss) scores the maximum, 100. A margin of **30 points or more** (roughly the empirical blowout threshold — close to a quarter of professional rugby matches finish at or beyond this gap) scores zero. Margins between 7 and 30 are interpolated linearly:

```
score = 100                                  if margin <= 7
score = 0                                    if margin >= 30
score = 100 × (30 − margin) / (30 − 7)       otherwise
```

(Corrected 2026\-09 — an earlier draft of this formula, `max(0, 1 − margin/30)`, didn't actually implement the flat 100 plateau at margin ≤ 7 described above; e.g. it scored a 7\-point margin at ~77 instead of 100. The piecewise version above matches what was agreed and is what's implemented in `scripts/scoring_engine.py`.)

### 2. Lead Changes / Momentum Swings

Counts "momentum swings" — both true lead changes (the team ahead switches sides) and ties (the trailing team draws level without overtaking) — reconstructed from the chronological scoreline. The match's opening score doesn't count (there's no prior leader to change from). Uses a diminishing\-returns curve rather than linear, since the jump from zero drama to some drama matters more than later increments:

| Momentum swings | Score |
| --- | --- |
| 0 | 0 |
| 1 | 50 |
| 2 | 75 |
| 3 | 90 |
| 4+ | 100 |

(Equivalent to roughly `100 × (1 − 0.5^N)`.)

### 3. Scoring Output (Tries vs. Kicks)

The share of total match points scored via tries: `(try + conversion points) / total match points`. A converted try's full value (7, or 5 if unconverted) counts as "try points," since the conversion is a direct consequence of the try rather than an independent tactical choice like a penalty kick. Penalty goals and drop goals are bucketed together as "kick points." Mapped linearly: 0% tries\-share → 0, 100% → 100. **Provisional** — to be checked against real URC data once the pipeline is live, since the ideal low/high anchors may need adjusting if real matches cluster tightly in a narrow range (the same issue Margin's raw scale would have had without anchoring).

A scoreless match (0 total points, a rare edge case) scores 0 for this parameter by definition.

### 4. Clutch / Last\-Minute Drama

Looks specifically at the final **10 minutes** of the match, combining two sub\-scores:

- **Margin sub\-score:** the final full\-time margin, using the same 7/30 scale as parameter 1.
- **Momentum sub\-score:** momentum swings (lead changes/ties) occurring *only* within the last 10 minutes, using the same diminishing\-returns curve as parameter 2. The 10\-minute window is measured back from the match's actual final minute (the `End` event, which can be past 80 with injury time), not a hardcoded 80.

The two are combined as `Clutch = 0.4 × MarginSubScore + 0.6 × MomentumSubScore` — momentum weighted higher than margin (since "something happened" late is more memorable than "it merely stayed close"). This design deliberately reuses the same underlying signals as parameters 1 and 2, weighted more heavily because they matter more when true right at the end — and it correctly scores a late\-developing blowout (a close game that one team pulls away with in the closing stretch) at or near zero automatically: the full\-time margin will already be large by then, with no special\-case rule required.

### 5. Upset / Favorite

No suitable external power rating or betting\-odds source is available for URC (checked and ruled out — no live public club rating exists, and odds parsing is out of scope for now). Instead, this is computed from a lightweight **Elo rating system maintained internally**:

- Each team starts at a baseline rating of **1500**, seeded from historical results where available so there's no "cold start" problem at the beginning of a season.
- A fixed home\-advantage bonus of **65 Elo points** is added to the home team's rating before computing each match's win probability via the standard Elo formula (`P(A beats B) = 1 / (1 + 10^((R_B − R_A)/400))`). This is applied only for the probability/margin calculation, not stored permanently on the team's rating.
- **K\-factor: 20** — moderate, since rugby's higher scoring variance than e.g. soccer means a single result should move ratings less aggressively than a lower\-scoring sport's Elo would.
- Ratings update after each match using a margin\-of\-victory multiplier adapted from FiveThirtyEight's NFL Elo model (`ln(margin + 1) × 2.2 / (0.001 × ratingDiff + 2.2)`) — a big win over a weaker team barely moves the rating further (already expected), while an equally big win over a stronger team moves it more (genuine signal).
- **Season carryover:** rather than resetting or fully preserving ratings between seasons, each team's rating regresses 25% of the way back toward the 1500 baseline at the start of a new season, to account for typical squad turnover without discarding a team's history entirely.
- The score for this parameter reflects how unlikely the actual winner was to win, based on ratings as they stood immediately before that match: a heavy favorite winning as expected scores low; a genuine upset scores high. `UpsetScore = 100 × (1 − winProbabilityOfActualWinner)`.

**Note:** the specific constants above (65\-point home advantage, K=20, the MOV formula, 25% season regression) are a reasoned v1 starting point — same caveat as the Final Formula weights below — implemented in `scripts/elo.py` and validated there against synthetic cases (expected results barely move ratings; genuine upsets move them a lot). They haven't yet been tuned against real multi\-season URC history.

### Final Formula

| Parameter | Weight |
| --- | --- |
| Margin | 20% |
| Lead Changes / Momentum | 20% |
| Clutch / Last\-Minute Drama | 25% |
| Scoring Output (Tries vs. Kicks) | 20% |
| Upset / Favorite | 15% |

`Entertainment Score = 0.20 × Margin + 0.20 × Momentum + 0.25 × Clutch + 0.20 × ScoringOutput + 0.15 × Upset`

Output range: **0–100**. Margin, Momentum, and Clutch together account for 65% of the total, so overall competitiveness dominates the score, with style of play (Scoring Output) and narrative surprise (Upset) as meaningful secondary contributors.

**Note:** these weights are a reasoned v1 starting point, not empirically derived the way the Margin anchors are. Once real match data is flowing through the pipeline, the formula should be sanity\-checked against a handful of matches URC fans already agree were classics (and a few known duds), and the weights adjusted from there if the resulting ranking doesn't feel right.

**Implementation status (2026\-09):** All five parameters are implemented and validated end\-to\-end against real match/season data — see "Data Pipeline" below.

## Data Pipeline

`scripts/run_pipeline.py` is the combined script the eventual GitHub Actions workflow (Step 6) will run on a schedule. Each run:

1. Fetches the current season's match list from the InCrowd feed (`scripts/feed_client.py` — the shared request logic from Step 1, factored out once multiple scripts needed it).
2. Adds any newly\-completed matches to a local **results ledger** (`scripts/sample_data/results_ledger.json`) — a flat, chronological history of every match result seen so far, seeded from `scripts/fetch_season_results.py`'s historical backfill via `scripts/init_ledger.py`. This ledger is what keeps the Elo ratings (`scripts/build_elo_ratings.py`) current as each new matchday completes, without re\-fetching detail for matches that are already known and old.
3. (Re)computes the full 5\-parameter score for any match that's either brand new, or was completed within the last **3 days** (a "recheck window," in case the data provider corrects something after the fact — see the Proposed fetch/correction cycle below). Already\-scored older matches are skipped entirely, with no fetch at all.
4. Writes the result to `docs/data/scores.json` — the **public, spoiler\-safe output**, and the only file this pipeline produces that the eventual static frontend (Step 5) should ever read. Each entry has the match id, date, competition, team names, and the five sub\-scores plus the overall 0–100 score. Nothing else. The file is only rewritten if something actually changed, keeping git history clean per the Proposed fetch/correction cycle.

Everything under `scripts/sample_data/` (the ledger, season backfills, single\-match samples) contains real scores/results and is `.gitignore`d; only `docs/data/scores.json` (and the rest of `docs/`) is meant to be committed.

**Validated (2026\-09):** the full pipeline was dry\-run with the network layer mocked (real scoring/Elo logic, fixture data standing in for the live feed) to confirm the bootstrap, skip\-if\-already\-scored, and only\-write\-if\-changed logic all behave correctly. It was then run for real against the live feed — `python scripts/run_pipeline.py 202501` (the season\-override backfill mode) scored all 151 completed matches from the 2025–26 season into `docs/data/scores.json`. A spot check confirmed no raw score, margin, or winner is present anywhere in that file — only match names, dates, and the five 0–100 sub\-scores. Not yet run on an actual schedule (that's Step 6); the current 2026–27 season hadn't started as of this validation, so ongoing in\-season runs are untested.

## Frontend

`docs/index.html` + `docs/style.css` + `docs/app.js` — a single static page, no build step or framework, that fetches `docs/data/scores.json` client\-side and renders a ranked, expandable list of matches. Each entry shows the two team names, the date, competition, and the overall 0–100 score; expanding it reveals the five sub\-score bars (Margin, Momentum, Clutch, Tries vs. Kicks, Upset). A sort control toggles between "most entertaining first" (default) and "most recent first."

**Score tiers (2026\-09, not yet discussed — flagging for confirmation):** the overall score is bucketed into a label for quick scanning: **80\+ "Must Watch"**, **60–79 "Good Watch"**, **40–59 "Okay"**, **below 40 "Skippable"**. These thresholds were picked by eyeballing the distribution of the 151 backfilled 2025–26 scores, not derived from anything more rigorous — worth revisiting once more seasons of data exist, the same way the Final Formula weights are flagged for recalibration.

**Validated (2026\-09):** rendered headlessly against the real 151\-match dataset — all matches render, sort toggling works, and an automated scan of the rendered page's visible text found no score\-like patterns (e.g. "36-7") anywhere, confirming the spoiler boundary holds all the way through to what a visitor actually sees, not just in the underlying JSON.

## Architecture & Hosting

The proposed stack: a static site on **GitHub Pages**, kept up to date by a scheduled **GitHub Actions** workflow that fetches match data, computes the entertainment score, and commits the result back into the repo. This is a well\-established pattern (sometimes called "git scraping") and fits the zero\-spoilers requirement particularly well.

### Why this fits

- **Free.** GitHub Pages is free for public repos (soft limits: \~100GB/month bandwidth, \~1GB site size — no concern for this project). GitHub\-hosted Actions runner minutes are unlimited/free on public repos too, so there's no cost pressure from running frequent data\-fetch jobs.
- **No separate backend needed.** The Actions runner acts as the backend: it's the only place that ever touches raw match data (scores, tries, cards). Only the derived entertainment score gets written into the repo and published — the raw result never reaches the static site or the browser, which matches the trust\-boundary described in the Data Sources section above.
- **Custom build step.** Deploying via a GitHub Actions workflow (rather than the default Jekyll pipeline) removes the "10 builds/hour" throttle, so the site can redeploy as often as the data workflow needs to.

### Scheduling caveats to design around

- **Timing isn't guaranteed.** GitHub explicitly states scheduled workflows can be delayed 5–30\+ minutes during high load, especially at the top of the hour. Scheduling at off\-peak minutes (e.g. `:07`, `:23`, `:37`) instead of `:00` helps.
- **Minimum interval is 5 minutes**, though there's no need to poll that tightly.
- **Auto\-disable after 60 days of repo inactivity** (public repos only) — relevant here since URC has an off\-season. Needs either a periodic keepalive commit or a manual check before each new season starts.
- Scheduled workflows only fire from the default branch.
- Workflow schedules support a `timezone:` field, useful since kickoffs are in UK/Ireland/Italy/SA time rather than UTC.

### Proposed fetch/correction cycle

Rather than timing one job per kickoff (kickoffs vary across a matchday), a more robust approach:

1. **Matchday polling:** a workflow runs every 30–60 minutes during known matchday windows (e.g. Friday evening through Sunday evening). Each run checks fixture statuses and processes any match that just turned "final" and hasn't been scored yet — computes the score and commits the result.
2. **Deploy on push:** the commit to the default branch triggers the Pages deploy workflow, republishing the site with the new score.
3. **Correction pass:** implemented as a rolling **3\-day recheck window** rather than a separate scheduled job — every run of `scripts/run_pipeline.py` re\-scores any match completed within the last 3 days (not just brand\-new ones), catching late corrections from the data provider, and only rewrites `docs/data/scores.json` if a result actually changed (keeps git history clean).

### Implementation note

The workflow's default `GITHUB_TOKEN` can commit and push back to the repo once "Read and write permissions" is enabled for Actions in repo settings (`contents: write`) — no extra secrets needed for that part. Deploying to Pages via an Actions workflow additionally needs `pages: write` permission, unless deploying via a plain `gh-pages` branch push instead.

## Step 6 — Scheduled updates (implemented, 2026-09)

`.github/workflows/update-scores.yml` runs the pipeline automatically instead of relying on someone to run `run_pipeline.py` by hand.

**Schedule:** two `cron` triggers cover matchday vs. off-matchday cadence — every 30 min from 11:00–23:00 UTC on Fri/Sat/Sun (`7,37 11-23 * * 5,6,0`), and hourly in the same window Mon–Thu (`7 11-23 * * 1,2,3,4`) to catch the occasional rescheduled fixture. Both use `:07`/`:37` rather than `:00`/`:30` per the scheduling caveat above about GitHub delaying jobs queued at the top of the hour. A `workflow_dispatch` trigger is also included so a run can be kicked off manually from the Actions tab — useful for testing, since the cron schedule itself won't fire on demand and the 2026–27 season hadn't produced a completed match as of this writing.

**The statelessness problem:** `scripts/sample_data/` — including `results_ledger.json`, which seeds the Elo ratings — is gitignored on purpose, since it holds raw scores. But every Actions run starts from a brand-new checkout with nothing outside git history, so a naive workflow would rebuild Elo from scratch (no history) on every run, defeating the point of carrying ratings across seasons.

**Fix:** rather than persisting state between runs, each run cheaply *rebuilds* the ledger by re-fetching the historical seasons (`fetch_season_results.py 202301 202401 202501`) before scoring. This is inexpensive because the match-list endpoint returns final scores directly — no per-match detail call needed — so it's 3 lightweight requests, not hundreds, and `init_ledger.py`'s dedup on `(date, home_id, away_id)` makes it idempotent. Once the 2026–27 season (`202601`) finishes, it needs to be added to that season list so future runs keep accumulating history — noted as a comment directly in the workflow file as a reminder.

**Commit identity:** automated commits use the standard `github-actions[bot]` identity (`github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>`), not a personal name/email, consistent with keeping personal identity out of the repo (see the privacy pass that led to the fresh-repo migration). The job only commits `docs/data/scores.json`, and only when it actually changed (`git diff --staged --quiet` guard) — no empty commits.

**Required one-time repo setting:** the workflow declares `permissions: contents: write`, but that can only *narrow* what the repo-level default allows, not widen it. New repos default to read-only Actions permissions, so the push step fails until, in the repo: **Settings → Actions → General → Workflow permissions → "Read and write permissions"** is selected and saved.

**Testing:** since scheduled cron runs won't fire on demand and there's currently no live match to score, the way to validate the workflow end-to-end is the **Actions tab → "Update entertainment scores" → Run workflow** button (`workflow_dispatch`), then check the run log and confirm `docs/data/scores.json` is unchanged (expected — no new matches) with no errors. This substitutes for a live scheduled run until the 2026–27 season produces a completed match (Step 8).
