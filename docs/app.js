// URC Replay Picks - reads the pre-computed, spoiler-safe scores at
// data/scores.json (written by scripts/run_pipeline.py) and renders a
// ranked list. This file never sees a raw score or result - the data
// it fetches literally doesn't contain any.

const DATA_URL = "data/scores.json";

const SUB_SCORE_LABELS = [
  ["margin", "Margin"],
  ["momentum", "Momentum"],
  ["clutch", "Clutch"],
  ["scoring_output", "Tries vs. Kicks"],
  ["upset", "Upset"],
];

function tierFor(overall) {
  if (overall >= 80) return { className: "tier-must", label: "Must Watch" };
  if (overall >= 60) return { className: "tier-good", label: "Good Watch" };
  if (overall >= 40) return { className: "tier-okay", label: "Okay" };
  return { className: "tier-skip", label: "Skippable" };
}

function formatDate(isoString) {
  const d = new Date(isoString);
  if (Number.isNaN(d.getTime())) return isoString;
  return d.toLocaleDateString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function renderBreakdown(scores) {
  return SUB_SCORE_LABELS.map(([key, label]) => {
    const value = scores[key] ?? 0;
    return `
      <div class="breakdown-row">
        <span class="label">${label}</span>
        <span class="bar-track"><span class="bar-fill" style="width:${value}%"></span></span>
        <span class="value">${value.toFixed(0)}</span>
      </div>
    `;
  }).join("");
}

function renderMatch(match) {
  const overall = match.scores.overall;
  const tier = tierFor(overall);

  const li = document.createElement("li");
  li.innerHTML = `
    <details class="match-card">
      <summary>
        <span class="match-teams">
          <span class="teams">${match.home_team} vs ${match.away_team}</span>
          <span class="date">${formatDate(match.date)} &middot; ${match.competition}</span>
        </span>
        <span class="overall-badge ${tier.className}">
          <span class="score">${overall.toFixed(0)}</span>
          <span class="tier">${tier.label}</span>
        </span>
        <span class="expand-icon">&#9656;</span>
      </summary>
      <div class="breakdown">
        ${renderBreakdown(match.scores)}
      </div>
    </details>
  `;
  return li;
}

function sortMatches(matches, mode) {
  const sorted = [...matches];
  if (mode === "date") {
    sorted.sort((a, b) => new Date(b.date) - new Date(a.date));
  } else {
    sorted.sort((a, b) => b.scores.overall - a.scores.overall);
  }
  return sorted;
}

async function main() {
  const listEl = document.getElementById("match-list");
  const statusEl = document.getElementById("status");
  const sortSelect = document.getElementById("sort-select");

  let matches;
  try {
    const resp = await fetch(DATA_URL, { cache: "no-cache" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    matches = Object.values(data);
  } catch (err) {
    statusEl.textContent = "Couldn't load match data. Try refreshing the page.";
    console.error("Failed to load scores.json:", err);
    return;
  }

  if (matches.length === 0) {
    statusEl.textContent = "No scored matches yet - check back after the next matchday.";
    return;
  }

  statusEl.textContent = "";

  function render() {
    const mode = sortSelect.value;
    const sorted = sortMatches(matches, mode);
    listEl.innerHTML = "";
    for (const match of sorted) {
      listEl.appendChild(renderMatch(match));
    }
  }

  sortSelect.addEventListener("change", render);
  render();
}

main();
