# Pip's Projects - Social Media Automation

Automated video posting system for Pip's adventures across multiple social media platforms.

## Setup

### 1. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Configure Credentials

Copy the example environment file and add your credentials:

```bash
cp .env.example .env
```

Then edit `/Users/alimoe/Documents/GitHub/Pips_Projects/.env` with your actual API credentials:

#### YouTube API Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable YouTube Data API v3
4. Create OAuth 2.0 credentials
5. Get your Client ID, Client Secret, and Refresh Token
6. Add them to `.env`:
   ```
   YOUTUBE_API_CLIENT_ID=your_actual_client_id
   YOUTUBE_API_CLIENT_SECRET=your_actual_client_secret
   YOUTUBE_API_REFRESH_TOKEN=your_actual_refresh_token
   ```

#### Facebook/Instagram API Setup
1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Create a Facebook App
3. Add Instagram Graph API
4. Get a long-lived Page Access Token
5. Get your Facebook Page ID and Instagram Business Account ID
6. Add them to `.env`:
   ```
   FB_ACCESS_TOKEN=your_facebook_token
   FB_PAGE_ID=your_facebook_page_id
   IG_PAGE_ID=your_instagram_business_id
   ```

#### GitHub Token Setup (Required for Instagram)
Instagram requires a publicly accessible URL for videos. This script uploads videos to your GitHub repository temporarily to get a public URL.

1. Go to [GitHub Settings > Personal Access Tokens](https://github.com/settings/tokens)
2. Click **"Generate new token (classic)"**
3. Give it a name like "Pips Projects Instagram Upload"
4. Select scope: **`repo`** (Full control of private repositories)
5. Generate and copy the token
6. Add to `.env`:
   ```
   GITHUB_TOKEN=your_github_personal_access_token
   GITHUB_REPO=moe-a11y/Pips_Projects
   ```

**Note**: Videos are uploaded to the `instagram_videos/` folder in your repo and remain there for Instagram to access.

#### Imgur Setup (Recommended for Instagram)
Imgur is more reliable than GitHub for Instagram video hosting. Instagram's servers can reliably download from Imgur.

1. Go to [Imgur API](https://api.imgur.com/oauth2/addclient)
2. Sign in or create an Imgur account
3. Register an application:
   - **Application name**: Pip's Projects
   - **Authorization type**: Select **"OAuth 2 authorization without a callback URL"**
   - **Email**: Your email
   - **Description**: Video hosting for Instagram
4. Click **Submit**
5. Copy your **Client ID** (not the Client Secret)
6. Add to `.env`:
   ```
   IMGUR_CLIENT_ID=your_imgur_client_id
   ```

**Note**: The script will try Imgur first (if configured), then fallback to GitHub if needed.

#### TikTok API Setup (Optional)
1. Go to [TikTok Developers](https://developers.tiktok.com/)
2. Create an app and get access token
3. Add to `.env`:
   ```
   TIKTOK_ACCESS_TOKEN=your_tiktok_token
   ```

### 3. Add Videos and Captions

Place your video files in the `videos/` folder and add their captions to `captions.json`:

#### Using captions.json (Recommended)

Edit `captions.json` to add captions for your videos:

```json
{
  "my_video.mp4": {
    "title": "Pip's Magical Workshop Adventure",
    "description": "Watch Pip create magical bubbles in his workshop! 🦦✨ #PipsProjects #Otter #MagicalMoments #OtterLife"
  },
  "another_video.mp4": {
    "title": "Pip Explores the Garden",
    "description": "Join Pip on a garden adventure! 🌸🦦 #PipsProjects #Otter #Nature"
  }
}
```

The format is:
- **Key**: Exact filename of your video (must match exactly)
- **title**: Video title (used for YouTube, under 80 characters recommended)
- **description**: Caption/description with hashtags (used for all platforms)

#### Using .txt files (Legacy, still supported)

Alternatively, create a `.txt` file with the same name as your video:

```
videos/
  my_video.mp4
  my_video.txt  (optional, if not in captions.json)
```

Format of `.txt` file:
```
Title of the Video (first line, under 80 characters)
Description of the video with hashtags #PipsProjects #Otter
```

**Note**: The script will prioritize `captions.json` over `.txt` files. If neither exists, it will use default captions.

## Usage

### Local Testing

```bash
python3 post_script.py
```

The script will:
1. Find the first video in the `videos/` folder
2. Attempt to upload to all configured platforms
3. **Delete the video after successful upload to at least one platform**
4. Keep the video if all uploads fail (safety feature)

### Automated GitHub Actions

The workflow is configured to run twice daily at:
- 12:00 PM UTC
- 7:30 PM UTC

You can also trigger it manually from the Actions tab on GitHub.

## Features

- ✅ Multi-platform posting (YouTube, Facebook, Instagram, TikTok)
- ✅ Automatic video deletion after successful upload
- ✅ Safety: Video retained if all uploads fail
- ✅ Custom titles/descriptions via companion .txt files
- ✅ Automated scheduling via GitHub Actions
- ✅ Environment-based credential management

## File Structure

```
.
├── .env                        # Local credentials (DO NOT COMMIT)
├── .env.example               # Template for credentials
├── .gitignore                 # Prevents .env from being committed
├── post_script.py             # Main posting script
├── upload_to_social_media.py  # Legacy upload functions
├── requirements.txt           # Python dependencies
├── .github/
│   └── workflows/
│       └── post_videos.yml    # GitHub Actions workflow
└── videos/                    # Place videos here
```

## Important Notes

⚠️ **Never commit your `.env` file** - It contains sensitive credentials
✅ The `.gitignore` file is configured to prevent this
✅ Use GitHub Secrets for the automated workflow
✅ Videos are automatically deleted after successful upload

## Troubleshooting

If uploads fail:
- Check that credentials are correctly set in `.env`
- Verify API access tokens are not expired
- Check platform-specific requirements (file size, format, etc.)
- Instagram requires publicly accessible video URLs
- Review error messages in the console output
