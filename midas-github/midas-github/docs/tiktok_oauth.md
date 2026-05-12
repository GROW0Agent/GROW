# TikTok One-Time OAuth (5 minutes)

1. Go to https://developers.tiktok.com → Manage Apps → Create App
2. Add product: **Login Kit** + **Content Posting API**
3. Scopes: `user.info.basic`, `video.upload`, `video.publish`
4. Redirect URI: `https://example.com/callback` (placeholder — we'll grab the code from the URL)
5. Copy `Client Key` and `Client Secret` → add to GitHub Secrets

### Get refresh token (run this URL in your browser):
```
https://www.tiktok.com/v2/auth/authorize/?client_key=YOUR_CLIENT_KEY&scope=user.info.basic,video.upload,video.publish&response_type=code&redirect_uri=https://example.com/callback&state=midas
```
After approving, your browser redirects to `https://example.com/callback?code=XXXX&state=midas`. Copy the `code` value.

### Exchange code for tokens (run locally one time):
```bash
curl -X POST https://open.tiktokapis.com/v2/oauth/token/ \
  -d "client_key=YOUR_CLIENT_KEY" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "code=XXXX" \
  -d "grant_type=authorization_code" \
  -d "redirect_uri=https://example.com/callback"
```
Response has `access_token` and `refresh_token`. Save both to GitHub Secrets.

> The Content Posting API may post to your **Inbox** until your app is approved for direct-publish.
> First time after OAuth: open TikTok app → Inbox → confirm the video. After approval, fully autonomous.
