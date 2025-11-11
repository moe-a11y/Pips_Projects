import requests, time

FB_TOKEN = os.environ["FB_ACCESS_TOKEN"]  # long-lived token with IG permissions
IG_ID = os.environ["IG_PAGE_ID"]  # Instagram Business Account ID


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
