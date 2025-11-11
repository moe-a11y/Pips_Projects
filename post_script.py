import glob, os, time, requests
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Load environment variables from .env file (if available, for local testing)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available (e.g., in GitHub Actions), env vars already set
    pass

# Get credentials from environment
YT_CLIENT_ID = os.getenv("YOUTUBE_API_CLIENT_ID")
YT_CLIENT_SECRET = os.getenv("YOUTUBE_API_CLIENT_SECRET")
YT_REFRESH_TOKEN = os.getenv("YOUTUBE_API_REFRESH_TOKEN")
FB_TOKEN = os.getenv("FB_ACCESS_TOKEN")
IG_ID = os.getenv("IG_PAGE_ID")
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
TIKTOK_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN")


def upload_to_youtube(video_path, title, description):
    """Upload video to YouTube."""
    if not all([YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN]):
        raise Exception("YouTube credentials not configured")

    creds = Credentials.from_authorized_user_info(
        info={
            'refresh_token': YT_REFRESH_TOKEN,
            'client_id': YT_CLIENT_ID,
            'client_secret': YT_CLIENT_SECRET
        },
        scopes=['https://www.googleapis.com/auth/youtube.upload']
    )

    youtube = build('youtube', 'v3', credentials=creds)
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "categoryId": "24",  # Entertainment
                "tags": ["PipsProjects", "Otter", "Magic"],
            },
            "status": {
                "privacyStatus": "public",
                "madeForKids": True,
            },
        },
        media_body=media,
    )
    response = request.execute()
    print(f"YouTube upload complete: video ID = {response.get('id')}")


def upload_to_instagram(video_path, caption):
    """Upload video to Instagram as a Reel."""
    if not all([FB_TOKEN, IG_ID]):
        raise Exception("Instagram credentials not configured")

    # For Instagram, we need a publicly accessible URL
    # For now, we'll skip this or you need to implement upload_to_github_raw
    raise Exception("Instagram upload requires publicly accessible video URL. Please implement upload_to_github_raw() or use a file hosting service.")


def upload_to_facebook(video_path, description):
    """Upload video to Facebook page."""
    if not all([FB_TOKEN, FB_PAGE_ID]):
        raise Exception("Facebook credentials not configured")

    video_file = open(video_path, "rb")
    fb_url = f"https://graph.facebook.com/v17.0/{FB_PAGE_ID}/videos"
    res = requests.post(
        fb_url,
        data={"description": description, "access_token": FB_TOKEN},
        files={"source": video_file},
    )
    res_data = res.json()
    if "id" in res_data:
        print(f"Facebook video posted (ID {res_data['id']}).")
    else:
        raise Exception(f"FB video upload failed: {res_data}")


def upload_to_tiktok(video_path, description):
    """Upload video to TikTok."""
    if not TIKTOK_TOKEN:
        raise Exception("TikTok credentials not configured")

    init_res = requests.post(
        "https://open.tiktokapis.com/v2/post/upload/",
        headers={"Authorization": f"Bearer {TIKTOK_TOKEN}"},
        files={"video": open(video_path, "rb")},
        data={"description": description},
    )
    if init_res.status_code == 200:
        print("TikTok upload successful.")
    else:
        raise Exception(f"TikTok upload failed: {init_res.text}")


def main():
    # 1. Find the video file in 'videos' folder
    video_files = glob.glob("videos/*.*")
    if not video_files:
        print("No video file found in the videos/ folder. Exiting without posting.")
        return
    video_path = video_files[0]
    print(f"Found video file: {video_path}")

    # 2. Prepare title and description for the post
    # For simplicity, derive them from the file name or a companion text file.
    # E.g., assume filename like "pip_magical_bubbles.mp4" and maybe a .txt with description.
    title = "Pip's New Adventure"
    description = "Pip tries something magical in his workshop! #PipsProjects #Otter"  # Default fallback

    desc_file = Path(video_path).with_suffix(".txt")
    if desc_file.exists():
        # If a description file is provided alongside the video, use it
        description = desc_file.read_text().strip()
        # Optionally split a first line as title
        if "\n" in description:
            title_line, desc_text = description.split("\n", 1)
            if len(title_line) < 80:
                title = title_line
                description = desc_text.strip()
    print(f"Using title: {title}")
    print(f"Description/Caption: {description}")

    # Track successful uploads
    upload_success = False

    # 3. Post to YouTube
    try:
        upload_to_youtube(video_path, title, description)
        upload_success = True
        print("YouTube upload succeeded.")
    except Exception as e:
        print(f"YouTube upload failed: {e}")

    # 4. Post to Instagram
    try:
        upload_to_instagram(video_path, description)
        upload_success = True
        print("Instagram upload succeeded.")
    except Exception as e:
        print(f"Instagram upload failed: {e}")

    # 5. Post to Facebook
    try:
        upload_to_facebook(video_path, description)
        upload_success = True
        print("Facebook upload succeeded.")
    except Exception as e:
        print(f"Facebook upload failed: {e}")

    # 6. Post to TikTok (optional; ignore failure since it's bonus)
    tik_tok_token = os.getenv("TIKTOK_ACCESS_TOKEN")
    if tik_tok_token:
        try:
            upload_to_tiktok(video_path, description)
            upload_success = True
            print("TikTok upload succeeded.")
        except Exception as e:
            print(f"TikTok upload failed or not configured: {e}")

    # 7. Delete video file after successful upload
    # This works both locally and in GitHub Actions
    if upload_success:
        try:
            os.remove(video_path)
            print(f"✓ Successfully deleted video file: {video_path}")

            # Also delete the description file if it exists
            if desc_file.exists():
                os.remove(desc_file)
                print(f"✓ Successfully deleted description file: {desc_file}")
        except Exception as e:
            print(f"✗ Failed to delete video file: {e}")
    else:
        print("✗ No successful uploads. Video file retained in folder.")


if __name__ == "__main__":
    main()
