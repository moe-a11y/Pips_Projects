#!/usr/bin/env python3
"""
Daily video generation for Pip's Projects.

Takes the script produced by generate_script.py (pending_script.json) and
generates an 8-second vertical video with Veo on Vertex AI, using the
character/workshop/machine reference images in resources/ to keep Pip visually
consistent across every video.

Outputs:
  - videos/pip_<date>.mp4      (picked up by post_script.py)
  - video_info.json            (title + caption entry for the new video)
  - deletes pending_script.json on success
"""

import json
import mimetypes
import os
import sys
import time
from datetime import date
from pathlib import Path

from google import genai
from google.genai import types

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

PENDING_SCRIPT_FILE = Path("pending_script.json")
VIDEO_INFO_FILE = Path("video_info.json")
RESOURCES_DIR = Path("resources")
VIDEOS_DIR = Path("videos")

VEO_MODEL = os.getenv("VEO_MODEL", "veo-3.1-generate-001")
# Veo accepts at most 3 asset reference images
PREFERRED_REFERENCES = ["1.png", "2.png", "3.png"]
MAX_REFERENCES = 3
POLL_INTERVAL_SECONDS = 20
TIMEOUT_SECONDS = 20 * 60


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


def pick_reference_images():
    """
    Pick up to MAX_REFERENCES reference images from resources/.
    Prefers 1.png / 2.png / 3.png (character sheet, workshop, press); falls back
    to the first images found in the folder.
    """
    preferred = [
        RESOURCES_DIR / name
        for name in PREFERRED_REFERENCES
        if (RESOURCES_DIR / name).exists()
    ]
    if preferred:
        return preferred[:MAX_REFERENCES]

    fallback = sorted(
        p
        for p in RESOURCES_DIR.iterdir()
        if p.suffix.lower() in (".png", ".jpg", ".jpeg")
    )
    return fallback[:MAX_REFERENCES]


def load_reference(path):
    mime_type = mimetypes.guess_type(str(path))[0] or "image/png"
    image = types.Image(image_bytes=path.read_bytes(), mime_type=mime_type)
    return types.VideoGenerationReferenceImage(image=image, reference_type="asset")


def extract_video_bytes(client, generated_video):
    """Get raw video bytes from the operation result, wherever the SDK put them."""
    video = generated_video.video
    if getattr(video, "video_bytes", None):
        return video.video_bytes
    # Fallback: ask the SDK to download it (handles URI-based results)
    client.files.download(file=video)
    if getattr(video, "video_bytes", None):
        return video.video_bytes
    raise RuntimeError(
        f"Could not extract video bytes from result (uri={getattr(video, 'uri', None)})"
    )


def main():
    if not PENDING_SCRIPT_FILE.exists():
        print(
            "❌ No pending_script.json found. Run generate_script.py first "
            "(nothing to generate)."
        )
        sys.exit(1)

    script = json.loads(PENDING_SCRIPT_FILE.read_text())
    for key in ("title", "caption", "video_prompt"):
        if not script.get(key):
            print(f"❌ pending_script.json is missing '{key}'.")
            sys.exit(1)

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

    references = [load_reference(p) for p in pick_reference_images()]
    if references:
        print(f"Using {len(references)} reference image(s) from {RESOURCES_DIR}/")
    else:
        print("⚠️  No reference images found in resources/ — generating without them.")

    print(f"Generating video with {VEO_MODEL}...")
    print(f"  Prompt: {script['video_prompt'][:120]}...")

    config_kwargs = {
        "aspect_ratio": "9:16",
        "duration_seconds": 8,
        "number_of_videos": 1,
    }
    if references:
        config_kwargs["reference_images"] = references

    operation = client.models.generate_videos(
        model=VEO_MODEL,
        prompt=script["video_prompt"],
        config=types.GenerateVideosConfig(**config_kwargs),
    )

    # Poll until the long-running generation finishes
    start = time.time()
    while not operation.done:
        if time.time() - start > TIMEOUT_SECONDS:
            print("❌ Video generation timed out.")
            sys.exit(1)
        elapsed = int(time.time() - start)
        print(f"  ...still generating ({elapsed}s elapsed)")
        time.sleep(POLL_INTERVAL_SECONDS)
        operation = client.operations.get(operation)

    if operation.error:
        print(f"❌ Video generation failed: {operation.error}")
        sys.exit(1)

    generated = (operation.response and operation.response.generated_videos) or []
    if not generated:
        print(f"❌ No video returned. Full response: {operation.response}")
        sys.exit(1)

    video_bytes = extract_video_bytes(client, generated[0])

    # Save the video where post_script.py expects it
    VIDEOS_DIR.mkdir(exist_ok=True)
    video_date = script.get("date", date.today().isoformat())
    video_path = VIDEOS_DIR / f"pip_{video_date}.mp4"
    video_path.write_bytes(video_bytes)
    print(f"✓ Saved video: {video_path} ({len(video_bytes) / 1e6:.1f} MB)")

    # Register title + caption for post_script.py
    video_info = {}
    if VIDEO_INFO_FILE.exists():
        try:
            video_info = json.loads(VIDEO_INFO_FILE.read_text())
        except json.JSONDecodeError:
            print("⚠️  video_info.json is corrupt, rebuilding it.")
    video_info[video_path.name] = {
        "title": script["title"],
        "description": script["caption"],
    }
    VIDEO_INFO_FILE.write_text(json.dumps(video_info, indent=2) + "\n")
    print(f"✓ Updated {VIDEO_INFO_FILE}")

    # The script has been fully consumed
    PENDING_SCRIPT_FILE.unlink()
    print("✓ Removed pending_script.json — generation complete.")


if __name__ == "__main__":
    main()
