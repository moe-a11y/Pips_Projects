import base64, glob, json, os, requests, time
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
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO", "moe-a11y/Pips_Projects")  # Default repo


def load_video_info():
    """
    Load video information (titles and descriptions) from video_info.json file.

    Returns:
        dict: Dictionary mapping video filenames to their info
              Format: {"video.mp4": {"title": "...", "description": "..."}}
    """
    video_info_file = Path("video_info.json")
    if not video_info_file.exists():
        print("⚠️  No video_info.json file found. Creating empty one.")
        with open(video_info_file, "w") as f:
            json.dump({}, f, indent=2)
        return {}

    try:
        with open(video_info_file, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing video_info.json: {e}")
        return {}


def save_video_info(video_info_data):
    """
    Save video information back to video_info.json file.

    Args:
        video_info_data: Dictionary of video info to save
    """
    video_info_file = Path("video_info.json")
    with open(video_info_file, "w") as f:
        json.dump(video_info_data, f, indent=2)
    print(f"✓ Updated video_info.json")


def delete_video_info_for_video(video_filename):
    """
    Delete video info entry for a specific video from video_info.json.

    Args:
        video_filename: Name of the video file to remove info for
    """
    video_info = load_video_info()
    if video_filename in video_info:
        del video_info[video_filename]
        save_video_info(video_info)
        print(f"✓ Deleted video info for {video_filename} from video_info.json")
    else:
        print(f"ℹ️  No video info entry found for {video_filename} in video_info.json")


def upload_to_github_raw(video_path):
    """
    Upload video to GitHub repository and return the raw URL.

    Args:
        video_path: Local path to the video file

    Returns:
        str: Raw GitHub URL to access the video
    """
    if not GITHUB_TOKEN:
        raise Exception("GitHub token not configured")

    # Read video file and encode to base64
    with open(video_path, "rb") as video_file:
        video_content = video_file.read()

    # Encode to base64 for GitHub API
    encoded_content = base64.b64encode(video_content).decode("utf-8")

    # Generate unique filename based on original name
    video_filename = Path(video_path).name
    github_path = f"instagram_videos/{video_filename}"

    # GitHub API URL
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{github_path}"

    # Prepare commit data
    commit_data = {
        "message": f"Upload video for Instagram posting: {video_filename}",
        "content": encoded_content,
        "branch": "main",
    }

    # Add headers with authentication
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Check if file already exists (to update instead of create)
    check_response = requests.get(api_url, headers=headers)
    if check_response.status_code == 200:
        # File exists, need to include sha for update
        commit_data["sha"] = check_response.json()["sha"]

    # Upload to GitHub
    response = requests.put(api_url, headers=headers, json=commit_data)

    if response.status_code not in [200, 201]:
        raise Exception(f"GitHub upload failed: {response.text}")

    # Construct raw URL
    raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{github_path}"

    print(f"Video uploaded to GitHub: {raw_url}")
    return raw_url


def upload_to_youtube(video_path, title, description):
    """Upload video to YouTube."""
    if not all([YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN]):
        raise Exception("YouTube credentials not configured")

    creds = Credentials.from_authorized_user_info(
        info={
            "refresh_token": YT_REFRESH_TOKEN,
            "client_id": YT_CLIENT_ID,
            "client_secret": YT_CLIENT_SECRET,
        },
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )

    youtube = build("youtube", "v3", credentials=creds)
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

    if not GITHUB_TOKEN:
        raise Exception("GitHub token required for Instagram uploads (to host video)")

    # 1. Upload video to GitHub to get a publicly accessible URL
    video_url = upload_to_github_raw(video_path)

    # 2. Create IG media container
    create_url = f"https://graph.facebook.com/v17.0/{IG_ID}/media"
    params = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": FB_TOKEN,
    }
    res = requests.post(create_url, params=params)
    res_data = res.json()
    if "id" not in res_data:
        raise Exception(f"IG upload container creation failed: {res_data}")
    container_id = res_data["id"]
    print(f"IG container ID: {container_id}. Waiting for processing...")

    # 3. Poll for processing status (Instagram needs time to download the video)
    max_retries = 30
    for attempt in range(max_retries):
        time.sleep(10)  # Wait 10 seconds between checks
        status_url = f"https://graph.facebook.com/v17.0/{container_id}"
        status_res = requests.get(
            status_url,
            params={"fields": "status_code,status", "access_token": FB_TOKEN},
        )
        status_data = status_res.json()

        status_code = status_data.get("status_code")
        status_msg = status_data.get("status", "No status message")
        print(
            f"IG processing status (attempt {attempt + 1}/{max_retries}): {status_code} - {status_msg}"
        )

        if status_code == "FINISHED":
            break
        elif status_code == "ERROR":
            # Get more detailed error information
            error_msg = status_data.get("status", "Unknown error")
            raise Exception(
                f"IG video processing failed. Status: {status_code}, Message: {error_msg}, Full response: {status_data}"
            )
    else:
        raise Exception("IG video processing timeout - took too long")

    # 4. Publish the media container
    publish_url = f"https://graph.facebook.com/v17.0/{IG_ID}/media_publish"
    res2 = requests.post(
        publish_url, params={"creation_id": container_id, "access_token": FB_TOKEN}
    )
    res2_data = res2.json()
    if "id" in res2_data:
        print(f"Instagram Reel posted successfully (ID {res2_data['id']}).")
    else:
        raise Exception(f"IG publish failed: {res2_data}")


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
    video_filename = Path(video_path).name
    print(f"Found video file: {video_path}")

    # 2. Load video info (title & description) from video_info.json
    video_info_data = load_video_info()

    # Check if this video has an info entry
    if video_filename in video_info_data:
        video_info = video_info_data[video_filename]
        title = video_info.get("title", "Pip's New Adventure")
        description = video_info.get(
            "description",
            "Pip tries something magical in his workshop! #PipsProjects #Otter",
        )
        print(f"✓ Found video info in video_info.json for {video_filename}")
    else:
        # Fallback to .txt file if no info in JSON
        print(
            f"⚠️  No video info found in video_info.json for {video_filename}, checking for .txt file..."
        )
        title = "Pip's New Adventure"
        description = (
            "Pip tries something magical in his workshop! #PipsProjects #Otter"
        )

        desc_file = Path(video_path).with_suffix(".txt")
        if desc_file.exists():
            # If a description file is provided alongside the video, use it
            content = desc_file.read_text().strip()
            # Optionally split a first line as title
            if "\n" in content:
                title_line, desc_text = content.split("\n", 1)
                if len(title_line) < 80:
                    title = title_line
                    description = desc_text.strip()
            else:
                description = content
            print(f"✓ Using description from {desc_file}")
        else:
            print(f"⚠️  No .txt file found either, using default description")

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

    # 7. Delete video file and caption after successful upload
    # This works both locally and in GitHub Actions
    if upload_success:
        try:
            os.remove(video_path)
            print(f"✓ Successfully deleted video file: {video_path}")

            # Delete the video info entry from video_info.json
            delete_video_info_for_video(video_filename)

            # Also delete the description .txt file if it exists (legacy support)
            desc_file = Path(video_path).with_suffix(".txt")
            if desc_file.exists():
                os.remove(desc_file)
                print(f"✓ Successfully deleted description file: {desc_file}")

            # Delete the video from instagram_videos folder if it exists
            instagram_video_path = Path(f"instagram_videos/{video_filename}")
            if instagram_video_path.exists():
                os.remove(instagram_video_path)
                print(
                    f"✓ Successfully deleted Instagram video file: {instagram_video_path}"
                )
        except Exception as e:
            print(f"✗ Failed to delete video file: {e}")
    else:
        print("✗ No successful uploads. Video file retained in folder.")


if __name__ == "__main__":
    main()
