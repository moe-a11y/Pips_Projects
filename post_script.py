import glob, os
from pathlib import Path

# Functions from earlier sections (YouTube, Instagram, Facebook, TikTok)
# ... (include upload_to_youtube, upload_to_instagram, upload_to_facebook, upload_to_tiktok as defined above) ...


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
    title = "Pip’s New Adventure"
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

    # 3. Post to YouTube
    try:
        upload_to_youtube(video_path, title, description)
    except Exception as e:
        print(f"YouTube upload failed: {e}")

    # 4. Post to Instagram
    try:
        upload_to_instagram(video_path, description)
    except Exception as e:
        print(f"Instagram upload failed: {e}")

    # 5. Post to Facebook
    try:
        upload_to_facebook(video_path, description)
    except Exception as e:
        print(f"Facebook upload failed: {e}")

    # 6. Post to TikTok (optional; ignore failure since it's bonus)
    tik_tok_token = os.getenv("TIKTOK_ACCESS_TOKEN")
    if tik_tok_token:
        try:
            upload_to_tiktok(video_path, description)
        except Exception as e:
            print(f"TikTok upload failed or not configured: {e}")


if __name__ == "__main__":
    main()
