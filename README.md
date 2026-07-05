# Pip's Projects — Fully Automated Daily Video Pipeline

Every day, this repo generates a brand-new 8-second video of **Pip the Otter** running a whimsical experiment in his magical workshop (starring his Mystical Hydraulic Press), writes a caption for it, and posts it to YouTube Shorts, Instagram Reels, Facebook Reels, and (optionally) TikTok. No humans involved.

## How It Works

Two GitHub Actions workflows run daily:

```
12:00 PM UTC — .github/workflows/generate_content.yml
  1. generate_script.py  → Gemini (Vertex AI) writes today's script + caption
       • uses SCRIPT_GENERATOR_PROMPT.md (character bible, style, format rules)
       • uses Google Search grounding for holidays/season/trends
       • checks content_history.json so concepts never repeat
       • writes pending_script.json, appends to content_history.json
  2. generate_video.py   → Veo (Vertex AI) generates the 8s 9:16 video
       • uses resources/1.png, 2.png, 3.png as character/press reference images
       • saves videos/pip_<date>.mp4 and registers it in video_info.json
  3. Commits videos/ + video_info.json + content_history.json to main

7:30 PM UTC — .github/workflows/post_videos.yml
  4. post_script.py      → posts the video to every configured platform
       • tracks per-platform success in video_info.json ("posted" key)
       • on partial failure: keeps the video, exits nonzero (so the run alerts),
         and the next run retries ONLY the platforms that failed
       • once ALL configured platforms have posted: deletes the video locally,
         from instagram_videos/ hosting, and from video_info.json
  5. Commits the resulting state back to main
```

Both workflows can also be triggered manually from the Actions tab.

## File Map

```
SCRIPT_GENERATOR_PROMPT.md   # The creative brief sent to Gemini every day
generate_script.py           # Step 1: script + caption generation
generate_video.py            # Step 2: Veo video generation
post_script.py               # Step 3: multi-platform posting + cleanup
get_youtube_token.py         # One-time local helper: mint YouTube refresh token
content_history.json         # Log of past concepts (novelty check)
video_info.json              # Title/caption + per-platform posted state
pending_script.json          # Transient: script waiting to be turned into video
resources/                   # Reference images (1=Pip+press scene, 2=character
                             #   sheet, 3=press prop) — fed to Veo for consistency
videos/                      # Generated videos awaiting posting
instagram_videos/            # Temporary public hosting for Meta ingestion
.github/workflows/           # The two daily cron workflows
```

## Setup

### 1. Install dependencies (local testing)

```bash
pip3 install -r requirements.txt
cp .env.example .env   # then fill in credentials
```

### 2. Google Cloud (content generation)

1. Create a GCP project with the **Vertex AI API** enabled.
2. Create a service account with the **Vertex AI User** role and download its JSON key.
3. Locally: point `GOOGLE_APPLICATION_CREDENTIALS` in `.env` at the key file (never commit it — it's gitignored).
4. GitHub Actions: paste the entire JSON key into a repo secret named **`GOOGLE_CREDENTIALS_JSON`**.

Models default to `gemini-2.5-pro` (script) and `veo-3.1-generate-001` (video); override via `GEMINI_MODEL` / `VEO_MODEL` env vars if needed.

### 3. YouTube

1. In [Google Cloud Console](https://console.cloud.google.com/), enable **YouTube Data API v3** and create OAuth 2.0 credentials.
2. Run `python3 get_youtube_token.py` locally (it opens a browser) to mint a refresh token.
3. Set `YOUTUBE_API_CLIENT_ID`, `YOUTUBE_API_CLIENT_SECRET`, `YOUTUBE_API_REFRESH_TOKEN`.

### 4. Facebook / Instagram

1. Create an app at [Facebook Developers](https://developers.facebook.com/) with the Instagram Graph API.
2. Get a long-lived Page access token, your Facebook Page ID, and your Instagram Business Account ID.
3. Set `FB_ACCESS_TOKEN`, `FB_PAGE_ID`, `IG_PAGE_ID`.

⚠️ Instagram ingestion requires a **publicly downloadable video URL**. The script commits the video to `instagram_videos/` in this repo and serves it via `raw.githubusercontent.com` — which means **this repo must stay public** for Instagram posting to work.

### 5. GitHub token

Create a classic PAT with `repo` scope and set it as the **`GH_TOKEN`** repo secret (used by the workflows to push commits and by the script for video hosting). Locally, set `GITHUB_TOKEN` in `.env`.

### 6. TikTok (optional)

Get a Content Posting API access token (`video.publish` scope) from [TikTok Developers](https://developers.tiktok.com/) and set `TIKTOK_ACCESS_TOKEN`. Note: direct posting requires TikTok app audit approval. If unset, TikTok is skipped.

### GitHub Actions secrets checklist

| Secret | Used by |
|---|---|
| `GOOGLE_CREDENTIALS_JSON` | generation workflow |
| `YOUTUBE_API_CLIENT_ID` / `_SECRET` / `_REFRESH_TOKEN` | posting workflow |
| `FB_ACCESS_TOKEN`, `FB_PAGE_ID`, `IG_PAGE_ID` | posting workflow |
| `GH_TOKEN` | both workflows |
| `TIKTOK_ACCESS_TOKEN` (optional) | posting workflow |

## Running Locally

```bash
python3 generate_script.py   # writes pending_script.json + updates history
python3 generate_video.py    # writes videos/pip_<date>.mp4 + video_info.json
python3 post_script.py       # posts everywhere, cleans up when all succeed
```

You can also drop a manually-made video into `videos/` with an entry in `video_info.json` (key = exact filename, fields = `title`, `description`) — or a legacy companion `.txt` (first line title, rest description) — and run `post_script.py` directly.

## Behavior Notes

- **Retry-safe posting**: a platform is never posted to twice; per-platform success is stored under `posted` in the video's `video_info.json` entry.
- **Failure alerting**: `post_script.py` exits nonzero when any configured platform fails, which fails the Actions run (GitHub emails you). Generation failures fail their run the same way.
- **Novelty**: `content_history.json` keeps every concept ever used; the last 120 are shown to Gemini with instructions not to repeat any.
- **YouTube audience**: uploads are marked **not made for kids** (general audience).
- Videos are marked public and posted immediately; there is no human review step by design.

## Troubleshooting

- Check the failed Actions run's logs — every step prints exactly what succeeded or failed.
- Meta tokens expire: long-lived Page tokens last ~60 days unless generated via a System User.
- YouTube refresh tokens can be revoked if unused — re-run `get_youtube_token.py` locally and update the secret.
- If Instagram processing times out, verify the repo is public and the video is <100 MB (GitHub raw limit).
- Repo size: hosting videos via git commits leaves blobs in history permanently. If the repo grows too large, periodically rewrite history or switch hosting to a GCS bucket.
