import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Any

import requests

# Basic config
USERNAME = "BrunoDrezza"
CURRENT_YEAR = datetime.now(timezone.utc).year
TOKEN = os.getenv("GH_TOKEN")


def fetch_events(username: str, year: int, max_pages: int = 10, per_page: int = 100) -> List[Dict[str, Any]]:
    """Fetch public events for the user and keep only events from the given year."""
    if not username:
        raise ValueError("USERNAME cannot be empty.")

    base_url = f"https://api.github.com/users/{username}/events/public"
    headers = {"Accept": "application/vnd.github+json"}

    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    session = requests.Session()
    events_for_year: List[Dict[str, Any]] = []

    for page in range(1, max_pages + 1):
        resp = session.get(
            base_url,
            params={"page": page, "per_page": per_page},
            headers=headers,
            timeout=10,
        )

        if resp.status_code != 200:
            raise RuntimeError(
                f"GitHub API error (status {resp.status_code}): {resp.text}"
            )

        page_events = resp.json()
        if not page_events:
            break

        for event in page_events:
            created_at = event.get("created_at")
            if not created_at:
                continue

            try:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                continue

            if dt.year == year:
                events_for_year.append(event)
            elif dt.year < year:
                # events are returned newest -> oldest; once we hit an older year we can stop
                return events_for_year

    return events_for_year


def compute_stats(events: List[Dict[str, Any]]) -> Dict[str, int]:
    """Compute some simple stats from the events list."""
    stats = {
        "total_events": 0,
        "push_events": 0,
        "commits": 0,
        "pull_requests_opened": 0,
        "issues_opened": 0,
        "repos_created": 0,
    }

    for event in events:
        stats["total_events"] += 1
        ev_type = event.get("type")
        payload = event.get("payload", {}) or {}

        if ev_type == "PushEvent":
            stats["push_events"] += 1
            commits = payload.get("commits") or []
            stats["commits"] += len(commits)

        if ev_type == "PullRequestEvent" and payload.get("action") == "opened":
            stats["pull_requests_opened"] += 1

        if ev_type == "IssuesEvent" and payload.get("action") == "opened":
            stats["issues_opened"] += 1

        if ev_type == "CreateEvent" and payload.get("ref_type") == "repository":
            stats["repos_created"] += 1

    return stats


def generate_svg(stats: Dict[str, int], username: str, year: int, output_path: str = "stats.svg") -> None:
    """Generate a GitHub-style stats card as SVG."""
    total = stats["total_events"]
    commits = stats["commits"]
    pushes = stats["push_events"]
    prs = stats["pull_requests_opened"]
    issues = stats["issues_opened"]
    repos = stats["repos_created"]

    def fmt(n: int) -> str:
        return f"{n:,}".replace(",", ",")

    # simple “activity” percentage based on total events
    max_ref = 100
    percent = 0.0 if total <= 0 else min(total / max_ref, 1.0)
    radius = 38
    circumference = 2 * 3.14159265 * radius
    progress = circumference * (1 - percent)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="495" height="180" viewBox="0 0 495 180" role="img" aria-labelledby="title desc">
  <title id="title">{username}'s GitHub Stats {year}</title>
  <desc id="desc">
    GitHub public events statistics for {year}.
  </desc>

  <style>
    .card {{
      fill: #ffffff;
      stroke: #e4e2e2;
      stroke-width: 1;
      rx: 6;
      ry: 6;
    }}
    .title {{
      font: 600 18px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      fill: #24292e;
    }}
    .subtitle {{
      font: 400 12px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      fill: #586069;
    }}
    .label {{
      font: 400 13px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      fill: #24292e;
    }}
    .value {{
      font: 600 13px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      fill: #0366d6;
    }}
    .small {{
      font: 400 11px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      fill: #6a737d;
    }}
  </style>

  <!-- transparent background -->
  <rect x="0" y="0" width="495" height="180" fill="none" />

  <!-- card -->
  <rect x="0.5" y="0.5" width="494" height="179" class="card" />

  <!-- header -->
  <g transform="translate(24, 32)">
    <text class="title">{username}'s GitHub Stats ({year})</text>
    <text class="subtitle" y="18">Public events · approx. last 300 events from the GitHub API</text>
  </g>

  <!-- stats list -->
  <g transform="translate(32, 78)">
    <text class="label" x="0" y="0">⭐  Total events (this year):</text>
    <text class="value" x="260" y="0">{fmt(total)}</text>

    <text class="label" x="0" y="22">📝 Commits (Push events):</text>
    <text class="value" x="260" y="22">{fmt(commits)}</text>

    <text class="label" x="0" y="44">📦 Push events:</text>
    <text class="value" x="260" y="44">{fmt(pushes)}</text>

    <text class="label" x="0" y="66">🔀 PRs opened:</text>
    <text class="value" x="260" y="66">{fmt(prs)}</text>

    <text class="label" x="0" y="88">❗ Issues opened:</text>
    <text class="value" x="260" y="88">{fmt(issues)}</text>

    <text class="label" x="0" y="110">📁 Repos created:</text>
    <text class="value" x="260" y="110">{fmt(repos)}</text>
  </g>

  <!-- activity circle -->
  <g transform="translate(380, 95)">
    <circle cx="0" cy="0" r="{radius}" fill="none" stroke="#e1e4e8" stroke-width="8" />
    <circle
      cx="0"
      cy="0"
      r="{radius}"
      fill="none"
      stroke="#58a6ff"
      stroke-width="8"
      stroke-linecap="round"
      stroke-dasharray="{circumference:.2f}"
      stroke-dashoffset="{progress:.2f}"
      transform="rotate(-90)"
    />
    <text text-anchor="middle" class="value" y="5">{int(percent*100)}%</text>
    <text text-anchor="middle" class="small" y="24">activity</text>
  </g>

  <!-- footer -->
  <g transform="translate(24, 164)">
    <text class="small">Generated automatically with GitHub Actions · Year {year}</text>
  </g>
</svg>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg)


def main() -> None:
    if not TOKEN:
        print(
            "⚠️ WARNING: GH_TOKEN environment variable is not set. "
            "It may still work locally, but in GitHub Actions you MUST configure the GH_TOKEN secret.",
            file=sys.stderr,
        )

    print(f"➡️ Fetching events for {USERNAME} in {CURRENT_YEAR}...")
    events = fetch_events(USERNAME, CURRENT_YEAR)
    print(f"✅ Events found for {CURRENT_YEAR}: {len(events)}")

    stats = compute_stats(events)
    print(f"📊 Stats: {stats}")

    generate_svg(stats, USERNAME, CURRENT_YEAR)
    print("🖼️ File 'stats.svg' generated successfully.")


if __name__ == "__main__":
    main()