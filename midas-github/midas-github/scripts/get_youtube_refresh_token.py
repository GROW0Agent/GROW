#!/usr/bin/env python3
"""
RUN ONCE LOCALLY to get your YT_REFRESH_TOKEN.
Usage:
  pip install google-auth-oauthlib
  python scripts/get_youtube_refresh_token.py
Paste the printed refresh_token into GitHub Secrets as YT_REFRESH_TOKEN.
"""
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

CLIENT_CONFIG = {
    "installed": {
        "client_id": input("Paste YT_CLIENT_ID: ").strip(),
        "client_secret": input("Paste YT_CLIENT_SECRET: ").strip(),
        "redirect_uris": ["http://localhost"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, SCOPES)
creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
print("\n=== YOUR REFRESH TOKEN ===\n")
print(creds.refresh_token)
print("\nCopy this entire string into GitHub Secrets > YT_REFRESH_TOKEN")
