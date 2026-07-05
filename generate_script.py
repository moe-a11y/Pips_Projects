#!/usr/bin/env python3
"""
Daily script generation for Pip's Projects.

Sends SCRIPT_GENERATOR_PROMPT.md to Gemini (Vertex AI, authenticated via the
service account in GOOGLE_APPLICATION_CREDENTIALS) along with the log of past
concepts (content_history.json) so today's idea is never a repeat. Gemini is
given Google Search grounding so it can factor in current holidays, the season,
and trending short-form content.

Outputs:
  - pending_script.json   (consumed by generate_video.py)
  - content_history.json  (appended with today's concept for future novelty checks)
"""

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

from google import genai
from google.genai import types

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

PROMPT_FILE = Path("SCRIPT_GENERATOR_PROMPT.md")
HISTORY_FILE = Path("content_history.json")
PENDING_SCRIPT_FILE = Path("pending_script.json")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
# How many past concepts to include in the prompt for the novelty check
HISTORY_WINDOW = 120


def get_project_id():
    """Resolve the GCP project id from env or the service account key file."""
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    if project:
        return project
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and Path(creds_path).exists():
        with open(creds_path) as f:
            return json.load(f).get("project_id")
    return None


def load_history():
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except json.JSONDecodeError:
            print("⚠️  content_history.json is corrupt, starting fresh.")
    return []


def save_history(history):
    HISTORY_FILE.write_text(json.dumps(history, indent=2) + "\n")


def build_prompt(history):
    prompt = PROMPT_FILE.read_text()
    today = date.today().isoformat()

    recent = history[-HISTORY_WINDOW:]
    if recent:
        lines = "\n".join(
            f"- [{item['date']}] {item['concept_summary']}" for item in recent
        )
    else:
        lines = "(No previous videos yet — this is the first one!)"

    prompt = prompt.replace("{{TODAY}}", today)
    prompt = prompt.replace("{{RECENT_CONCEPTS}}", lines)
    return prompt


def parse_json_response(text):
    """Parse the model's JSON output, tolerating markdown fences or prose around it."""
    text = text.strip()
    # Strip a ```json ... ``` fence if present
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        # Fall back to the outermost JSON object
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError(f"No JSON object found in model response:\n{text}")
        text = text[start : end + 1]
    return json.loads(text)


def generate_script(client, prompt):
    """Call Gemini, preferring Google Search grounding for trend/holiday awareness."""
    configs = [
        # Preferred: with search grounding (trends, holidays)
        types.GenerateContentConfig(
            temperature=1.0,
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
        # Fallback: no tools (prompt still has evergreen guidance)
        types.GenerateContentConfig(temperature=1.0),
    ]

    last_error = None
    for config in configs:
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL, contents=prompt, config=config
            )
            return parse_json_response(response.text)
        except Exception as e:
            last_error = e
            print(f"⚠️  Generation attempt failed ({e}), trying fallback...")
    raise last_error


def main():
    project = get_project_id()
    if not project:
        print(
            "❌ No GCP project found. Set GOOGLE_APPLICATION_CREDENTIALS to your "
            "service account key file (or set GOOGLE_CLOUD_PROJECT)."
        )
        sys.exit(1)

    client = genai.Client(
        vertexai=True,
        project=project,
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
    )

    history = load_history()
    prompt = build_prompt(history)
    today = date.today().isoformat()

    print(f"Generating today's script ({today}) with {GEMINI_MODEL}...")
    script = generate_script(client, prompt)

    # Validate required fields
    required = ["concept_summary", "title", "caption", "video_prompt"]
    missing = [k for k in required if not script.get(k)]
    if missing:
        print(f"❌ Model response missing fields: {missing}\n{script}")
        sys.exit(1)

    script["date"] = today

    PENDING_SCRIPT_FILE.write_text(json.dumps(script, indent=2) + "\n")
    print(f"✓ Wrote {PENDING_SCRIPT_FILE}")
    print(f"  Concept: {script['concept_summary']}")
    print(f"  Title:   {script['title']}")

    # Log the concept so future runs never repeat it. Replace any existing
    # entry for today so a same-day rerun doesn't create duplicates.
    history = [h for h in history if h.get("date") != today]
    history.append(
        {
            "date": today,
            "concept_summary": script["concept_summary"],
            "title": script["title"],
        }
    )
    save_history(history)
    print(f"✓ Appended concept to {HISTORY_FILE} ({len(history)} total)")


if __name__ == "__main__":
    main()
