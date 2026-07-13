#!/usr/bin/env python3
"""
Regenerate docs/episodes.html from content_history.json.

Runs in the daily generation workflow after the script is written, so the
public website's episode log stays current forever with zero maintenance.
"""

import html
import json
from datetime import datetime
from pathlib import Path

HISTORY_FILE = Path("content_history.json")
OUTPUT_FILE = Path("docs/episodes.html")

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Episodes — Pip's Projects</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="The complete episode log of Pip's Projects — every daily experiment Pip has run in his magical workshop.">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <nav>
    <a class="brand" href="index.html">🦦 Pip's Projects</a>
    <a href="about.html">About</a>
    <a href="episodes.html">Episodes</a>
    <a href="contact.html">Contact</a>
  </nav>
  <main>
    <h1>Episode Log</h1>
    <p>Every experiment Pip has run so far — one per day, newest first. This page updates automatically the moment a new episode is produced. Watch them on YouTube Shorts, Instagram Reels, and Facebook Reels.</p>
{episodes}
  </main>
  <footer>
    <p>© 2026 Pip's Projects · <a href="terms.html">Terms of Service</a> · <a href="privacy.html">Privacy Policy</a> · <a href="contact.html">Contact</a></p>
  </footer>
</body>
</html>
"""

EPISODE_TEMPLATE = """    <div class="card episode">
      <div class="date">{date} · Episode {number}</div>
      <h3>{title}</h3>
      <p>{summary}</p>
    </div>"""


def pretty_date(iso_date):
    try:
        return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%B %-d, %Y")
    except ValueError:
        return iso_date


def main():
    history = json.loads(HISTORY_FILE.read_text()) if HISTORY_FILE.exists() else []

    cards = [
        EPISODE_TEMPLATE.format(
            date=html.escape(pretty_date(entry.get("date", ""))),
            number=i,
            title=html.escape(entry.get("title", "Untitled experiment")),
            summary=html.escape(entry.get("concept_summary", "")),
        )
        for i, entry in enumerate(history, start=1)
    ][::-1]  # newest first

    episodes = "\n".join(cards) if cards else '    <div class="card"><p>The very first experiment is coming soon — check back tomorrow!</p></div>'

    OUTPUT_FILE.write_text(PAGE_TEMPLATE.format(episodes=episodes))
    print(f"✓ Wrote {OUTPUT_FILE} with {len(cards)} episode(s)")


if __name__ == "__main__":
    main()
