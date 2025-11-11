import requests, time

FB_TOKEN = os.environ["FB_ACCESS_TOKEN"]  # long-lived token with IG permissions
IG_ID = os.environ["IG_PAGE_ID"]  # Instagram Business Account ID

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from oauth2client.client import GoogleCredentials

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

creds = Credentials.from_authorized_user_info(
    info={
      'refresh_token': REFRESH_TOKEN,
      'client_id': CLIENT_ID,
      'client_secret': CLIENT_SECRET
    },
    scopes=['https://www.googleapis.com/auth/youtube.upload']
)
creds.refresh()  # obtain new access token using refresh token
youtube_service = build('youtube', 'v3', credentials=creds)


# Assume credentials are provided via environment (from GH Secrets)
YT_CLIENT_ID = os.environ["YOUTUBE_API_CLIENT_ID"]
YT_CLIENT_SECRET = os.environ["YOUTUBE_API_CLIENT_SECRET"]
YT_REFRESH_TOKEN = os.environ["YOUTUBE_API_REFRESH_TOKEN"]


def upload_to_youtube(video_path, title, description):
    # Authenticate with OAuth 2 using the stored refresh token
    creds_data = {
        "client_id": YT_CLIENT_ID,
        "client_secret": YT_CLIENT_SECRET,
        "refresh_token": YT_REFRESH_TOKEN,
        "token_uri": "https://accounts.google.com/o/oauth2/token",
        "grant_type": "refresh_token",
    }
    creds = GoogleCredentials.from_stream(None)  # We'll construct manually
    creds.client_id = YT_CLIENT_ID
    creds.client_secret = YT_CLIENT_SECRET
    creds.refresh_token = YT_REFRESH_TOKEN
    creds.access_token = None  # force refresh
    creds.token_uri = "https://accounts.google.com/o/oauth2/token"
    creds.refresh(None)  # get new access token

    youtube = build("youtube", "v3", credentials=creds)
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "categoryId": "24",  # Category 24 = Entertainment (for example)
                "tags": ["PipsProjects", "Otter", "Magic"],  # add relevant tags
            },
            "status": {
                "privacyStatus": "public",
                "madeForKids": True,  # mark appropriately
            },
        },
        media_body=media,
    )
    response = request.execute()
    print(f"YouTube upload complete: video ID = {response.get('id')}")


def upload_to_instagram(video_path, caption):
    # 1. Upload video file somewhere accessible or get its URL
    # For simplicity, we’ll use GitHub raw file URL if the repo is public:
    video_url = upload_to_github_raw(
        video_path
    )  # (Define this to commit or use GH raw link)

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

    # 3. Poll for processing (avoid immediate publish if not ready)
    time.sleep(5)  # wait a few seconds for video processing on IG servers

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


FB_PAGE_ID = os.environ["FB_PAGE_ID"]


def upload_to_facebook(video_path, description):
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


TIKTOK_TOKEN = os.environ["TIKTOK_ACCESS_TOKEN"]


def upload_to_tiktok(video_path, description):
    init_res = requests.post(
        "https://open.tiktokapis.com/v2/post/upload/",
        headers={"Authorization": f"Bearer {TIKTOK_TOKEN}"},
        files={"video": open(video_path, "rb")},
        data={"description": description},
    )
    if init_res.status_code == 200:
        print("TikTok upload successful (check TikTok app to publish).")
    else:
        print(f"TikTok upload failed: {init_res.text}")
