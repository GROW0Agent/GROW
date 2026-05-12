# Instagram One-Time Setup (8 minutes)

## Requirements
- Instagram account converted to **Business** or **Creator** (Settings → Account → Switch)
- A **Facebook Page** linked to that IG account (in IG Settings → Linked Accounts)

## Get long-lived access token
1. Go to https://developers.facebook.com → My Apps → Create App → "Business" type
2. Add products: **Instagram Graph API**, **Facebook Login for Business**
3. Tools → **Graph API Explorer** → select your app
4. Permissions: `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`, `business_management`
5. Click "Generate Access Token" → approve
6. You now have a **short-lived token (1 hour)**. Convert to long-lived (60 days):

```
https://graph.facebook.com/v20.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_TOKEN
```

7. The returned `access_token` is your `IG_ACCESS_TOKEN` (60-day lifespan, refresh later via the same endpoint).

## Get your IG_USER_ID
```
GET https://graph.facebook.com/v20.0/me/accounts?access_token=LONG_TOKEN
```
Find your Page → copy its `id` → then:
```
GET https://graph.facebook.com/v20.0/PAGE_ID?fields=instagram_business_account&access_token=LONG_TOKEN
```
The `instagram_business_account.id` is your `IG_USER_ID`.

> Add a recurring monthly task to refresh the long-lived token (the analyst workflow will warn you when it's near expiry).
