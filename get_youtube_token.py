#!/usr/bin/env python3
"""
Helper script to generate a YouTube OAuth refresh token.

This script will:
1. Open a browser for you to authorize the app
2. Exchange the authorization code for a refresh token
3. Display the refresh token to add to your .env file or GitHub secrets

Prerequisites:
- Have your YouTube API Client ID and Client Secret ready
- Make sure you've enabled YouTube Data API v3 in Google Cloud Console
"""

import http.server
import os
import socketserver
import webbrowser
from threading import Thread
from urllib.parse import parse_qs, urlencode

import requests

# Load existing credentials from .env if available
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Get client ID and secret from environment or prompt user
CLIENT_ID = os.getenv("YOUTUBE_API_CLIENT_ID")
CLIENT_SECRET = os.getenv("YOUTUBE_API_CLIENT_SECRET")

if not CLIENT_ID:
    print("\nNo YOUTUBE_API_CLIENT_ID found in .env file.")
    CLIENT_ID = input("Enter your YouTube API Client ID: ").strip()

if not CLIENT_SECRET:
    print("\nNo YOUTUBE_API_CLIENT_SECRET found in .env file.")
    CLIENT_SECRET = input("Enter your YouTube API Client Secret: ").strip()

# OAuth settings
REDIRECT_URI = "http://localhost:8080"
SCOPES = "https://www.googleapis.com/auth/youtube.upload"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"

# Global variable to store the authorization code
auth_code = None


class OAuthHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler to capture the OAuth callback."""

    def do_GET(self):
        global auth_code

        # Parse the query string
        query_string = self.path.split("?", 1)[-1] if "?" in self.path else ""
        params = parse_qs(query_string)

        if "code" in params:
            auth_code = params["code"][0]
            # Send success response
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            success_html = """
            <html>
                <head><title>Authorization Successful</title></head>
                <body>
                    <h1>✅ Authorization Successful!</h1>
                    <p>You can close this window and return to the terminal.</p>
                </body>
            </html>
            """
            self.wfile.write(success_html.encode())
        else:
            # Send error response
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            error_html = """
            <html>
                <head><title>Authorization Failed</title></head>
                <body>
                    <h1>❌ Authorization Failed</h1>
                    <p>No authorization code received. Please try again.</p>
                </body>
            </html>
            """
            self.wfile.write(error_html.encode())

    def log_message(self, format, *args):
        """Suppress log messages."""
        pass


def start_callback_server():
    """Start a local server to receive the OAuth callback."""
    port = 8080
    handler = OAuthHandler
    httpd = socketserver.TCPServer(("", port), handler)
    print(f"Starting callback server on port {port}...")
    httpd.handle_request()  # Handle one request then stop
    httpd.server_close()


def main():
    print("\n" + "=" * 60)
    print("YouTube OAuth Refresh Token Generator")
    print("=" * 60)

    # Step 1: Build authorization URL
    auth_params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",  # Important: get refresh token
        "prompt": "consent",  # Force consent screen to get refresh token
    }

    auth_url = f"{AUTH_URL}?{urlencode(auth_params)}"

    print("\n📋 Step 1: Authorize the application")
    print("-" * 60)
    print("A browser window will open for you to authorize this app.")
    print("If it doesn't open automatically, copy this URL to your browser:")
    print(f"\n{auth_url}\n")

    input("Press Enter to open the browser...")

    # Open browser
    webbrowser.open(auth_url)

    # Start callback server in background
    print("\n⏳ Waiting for authorization...")
    start_callback_server()

    if not auth_code:
        print("\n❌ Failed to receive authorization code.")
        print(
            "Please try again and make sure to complete the authorization in the browser."
        )
        return

    print("\n✅ Authorization code received!")

    # Step 2: Exchange code for tokens
    print("\n📋 Step 2: Exchanging authorization code for refresh token...")
    print("-" * 60)

    token_data = {
        "code": auth_code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    response = requests.post(TOKEN_URL, data=token_data)

    if response.status_code != 200:
        print(f"\n❌ Failed to get tokens: {response.text}")
        return

    tokens = response.json()
    refresh_token = tokens.get("refresh_token")

    if not refresh_token:
        print("\n❌ No refresh token received.")
        print("This might happen if you've authorized this app before.")
        print("Try revoking access at: https://myaccount.google.com/permissions")
        print("Then run this script again.")
        return

    # Step 3: Display the refresh token
    print("\n" + "=" * 60)
    print("✅ SUCCESS! Your YouTube Refresh Token:")
    print("=" * 60)
    print(f"\n{refresh_token}\n")
    print("=" * 60)

    print("\n📝 Next Steps:")
    print("-" * 60)
    print("1. Copy the refresh token above")
    print("2. Update your .env file:")
    print(f"   YOUTUBE_API_REFRESH_TOKEN={refresh_token}")
    print("\n3. Update your GitHub repository secrets:")
    print(
        "   Go to: https://github.com/moe-a11y/Pips_Projects/settings/secrets/actions"
    )
    print("   Update the YOUTUBE_API_REFRESH_TOKEN secret with the new value")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
