import os
import sys
from datetime import datetime, timezone
import requests
from typing import Dict, List, Any

USERNAME = "BrunoDrezza"
CURRENT_YEAR = datetime.now(timezone.utc).year
TOKEN = os.getenv("GH_TOKEN")


def fetch_events(username: str, year: int, max_pages: int = 10, per_page: int = 100):
    base_url = f"https://api.github.com/users/{username}/events/public"
    headers = {"Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    events_year = []
    session = requests.Session()

    for page in range(1, max_pages + 1):
        r = session.get(
            base_url,
            params={"page": page, "per_page": per_page},
            headers=headers,
            timeout=10,
        )

        if r.status_code != 200:
            raise RuntimeError(f"GitHub API error {r.status_code}: {r.text}")

        events = r.json()
        if not events:
            break

        for e in events:
            created = e.get("created_at")
            if not created:
                continue

            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            if dt.year == year:
                events_year.append(e)
            elif dt.year < year:
                return events_year

    return events_year


def compute_stats(events: List[Dict[str, Any]]) -> Dict[str, int]:
    stats = {
        "total": 0,
        "push_events": 0,
        "commits": 0,
        "prs": 0,
        "issues": 0,
        "repos": 0,
    }

    for e in events:
        stats["total"] += 1
        t = e.get("type")
        p = e.get("payload", {}) or {}

        if t == "PushEvent":
            stats["push_events"] += 1
            stats["commits"] += len(p.get("commits") or [])

        if t == "PullRequestEvent" and p.get("action") == "opened":
            stats["prs"] += 1

        if t == "IssuesEvent" and p.get("action") == "opened":
            stats["issues"] += 1

        if t == "CreateEvent" and p.get("ref_type") == "repository":
            stats["repos"] += 1

    return stats


def generate_svg(stats, username, year, out="stats.svg"):
    total = stats["total"]
    commits = stats["commits"]
    pushes = stats["push_events"]
    prs = stats["prs"]
    issues = stats["issues"]
    repos = stats["repos"]

    def fmt(n):
        return f"{n:,}".replace(",", ".")

    # Activity circle math
    radius = 38
    circ = 2 * 3.14159265 * radius
    percent = min(total / 100, 1)
    progress = circ * (1 - percent)

    # 🟦 SVG final com layout corrigido
    svg = f"""
<svg xmlns="http://www.w3.org/2000/svg" width="520" height="240" viewBox="0 0 520 240">

  <style>
    .title {{ font: 600 20px system-ui; fill: #24292e; }}
    .subtitle {{ font: 400 13px system-ui; fill: #586069; }}
    .label {{ font: 400 14px system-ui; fill: #24292e; }}
    .value {{ font: 600 14px system-ui; fill: #0366d6; }}
    .small {{ font: 400 12px system-ui; fill: #6a737d; }}
    .card {{ fill: white; stroke: #e4e2e2; stroke-width: 1; rx: 8; }}
  </style>

  <rect width="520" height="240" fill="none"/>
  <rect x="0.5" y="0.5" width="519" height="239" class="card"/>

  <!-- Title -->
  <g transform="translate(26, 40)">
    <text class="title">{username}'s GitHub Stats ({year})</text>
    <text class="subtitle" y="22">Public events · approx. last 300 events from GitHub API</text>
  </g>

  <!-- Stats List -->
  <g transform="translate(26, 90)">
    <text class="label" x="0" y="0">⭐ Total events (this year):</text>
    <text class="value" x="250" y="0">{fmt(total)}</text>

    <text class="label" x="0" y="28">📝 Commits:</text>
    <text class="value" x="250" y="28">{fmt(commits)}</text>

    <text class="label" x="0" y="56">📦 Push events:</text>
    <text class="value" x="250" y="56">{fmt(pushes)}</text>

    <text class="label" x="0" y="84">🔀 PRs opened:</text>
    <text class="value" x="250" y="84">{fmt(prs)}</text>

    <text class="label" x="0" y="112">❗ Issues opened:</text>
    <text class="value" x="250" y="112">{fmt(issues)}</text>

    <text class="label" x="0" y="140">📁 Repos created:</text>
    <text class="value" x="250" y="140">{fmt(repos)}</text>
  </g>

  <!-- Activity circle -->
  <g transform="translate(400, 130)">
    <circle cx="0" cy="0" r="{radius}" fill="none" stroke="#e1e4e8" stroke-width="8"/>
    <circle cx="0" cy="0" r="{radius}" fill="none"
            stroke="#58a6ff" stroke-width="8" stroke-linecap="round"
            stroke-dasharray="{circ:.2f}" stroke-dashoffset="{progress:.2f}"
            transform="rotate(-90)"/>
    <text class="value" text-anchor="middle" y="5">{int(percent*100)}%</text>
    <text class="small" text-anchor="middle" y="25">activity</text>
  </g>

  <!-- Footer -->
  <g transform="translate(26, 220)">
    <text class="small">Generated automatically using GitHub Actions · Year {year}</text>
  </g>

</svg>
"""

    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)


def main():
    if not TOKEN:
        print("WARNING: GH_TOKEN not set", file=sys.stderr)

    events = fetch_events(USERNAME, CURRENT_YEAR)
    stats = compute_stats(events)
    generate_svg(stats, USERNAME, CURRENT_YEAR)


if __name__ == "__main__":
    main()
