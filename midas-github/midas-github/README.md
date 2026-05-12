# 🤖 PROJECT MIDAS — GitHub Actions Edition

Fully autonomous faceless content engine. **Zero servers. Zero credit card. Zero ongoing involvement.**

## What It Does (Automatically, Forever)

| Time (IST)  | Time (UTC) | Action |
|---|---|---|
| 6:00 AM  | 00:30 | Generate + post to **YouTube Shorts** |
| 12:00 PM | 06:30 | Generate + post to **TikTok** |
| 6:00 PM  | 12:30 | Generate + post to **Instagram Reels** |
| Mon 8:30 AM IST | 03:00 | Analyst rewrites prompts using last week's view data |

All runs are GitHub Actions. Free tier = 2,000 min/mo. Your usage = ~120 min/mo. **5% of free quota.**

---

## ⚡ One-Time Setup (~25 minutes, then never again)

### 1. Push this repo to GitHub
```bash
cd midas-github
git init && git add . && git commit -m "init"
git remote add origin https://github.com/GROW0Agent/midas.git
git push -u origin main
```

### 2. Add GitHub Secrets
Go to: `Settings → Secrets and variables → Actions → New repository secret`

| Secret | Value | Where to get it |
|---|---|---|
| `GROQ_API_KEY` | `gsk_...` | console.groq.com (free, no card) |
| `GEMINI_API_KEY` | `AIza...` | aistudio.google.com/apikey (free) |
| `PEXELS_API_KEY` | (your key) | pexels.com/api (free, no card) |
| `YT_CLIENT_ID` | OAuth client ID | console.cloud.google.com → enable YouTube Data API v3 → OAuth credentials → Desktop app |
| `YT_CLIENT_SECRET` | OAuth client secret | (same place) |
| `YT_REFRESH_TOKEN` | Refresh token | Run `python scripts/get_youtube_refresh_token.py` **locally one time** |
| `TIKTOK_CLIENT_KEY` | TikTok app client key | developers.tiktok.com → create app → enable Content Posting API |
| `TIKTOK_CLIENT_SECRET` | TikTok app secret | (same) |
| `TIKTOK_REFRESH_TOKEN` | Refresh token | one-time OAuth flow (instructions in `docs/tiktok_oauth.md`) |
| `TIKTOK_ACCESS_TOKEN` | Initial access token | (from same OAuth flow) |
| `IG_ACCESS_TOKEN` | Long-lived IG token | Convert IG to Business → link FB Page → developers.facebook.com → Graph API Explorer |
| `IG_USER_ID` | Your IG Business User ID | Graph API Explorer: `GET /me/accounts` |

> The repo's built-in `GITHUB_TOKEN` is auto-provided — no setup needed.

### 3. Enable Actions
- Tab `Actions` → "I understand my workflows, go ahead"
- Click `MIDAS - Generate & Post` → `Run workflow` → "Run" (manual test)
- Watch it succeed end-to-end on YouTube first. ✅

### 4. Walk away.
From midnight UTC tonight onward, MIDAS posts 3 videos/day and tunes itself weekly.

---

## 🧠 How It Auto-Improves Itself

Every Monday 03:00 UTC the **Analyst** workflow:
1. Pulls view/like/comment stats for all your YouTube uploads
2. Sorts winners vs losers
3. Asks Groq Llama 3.3 70B: *"Based on this performance data, rewrite the style guide and hook patterns to lean into what worked"*
4. Commits the new `config/prompt_template.json`

Next Tuesday's videos use the improved prompts. No human in the loop.

---

## 💰 Affiliate Income

When you join Amazon Associates / Digistore24 / Impact (free, ~10 min):
1. Open `config/prompt_template.json`
2. Set `"affiliate_link": "https://amzn.to/your-link"` and `"bio_link": "https://linktr.ee/yourbio"`
3. Commit. Every future video description will include them.

---

## 🛠 Files

| File | Role |
|---|---|
| `.github/workflows/generate-and-post.yml` | The 3x daily cron |
| `.github/workflows/analyst.yml` | The weekly tuning cron |
| `scripts/researcher.py` | Generates viral hooks via Groq |
| `scripts/creator.py` | Script → TTS → Pexels → MP4 |
| `scripts/distributor.py` | Uploads to YT / TikTok / IG |
| `scripts/analyst.py` | Weekly performance-driven tuning |
| `config/prompt_template.json` | Niche, voice, style — edit anytime |
| `content/hook_queue.json` | Pre-generated hooks (auto-managed) |
| `content/published.json` | Audit log of every post (auto-managed) |

---

## ⚠️ The Unavoidable Human Steps

Platform OAuth is **legally required** to be initiated by a human once. This is not bypassable:
- **YouTube**: Log into Google Cloud, OAuth consent screen, run the helper script once → paste refresh token
- **TikTok**: Approve your app in Developer Portal, run OAuth once → paste tokens
- **Instagram**: Convert to Business account, link to a Facebook Page, generate long-lived token once

After this, the tokens auto-refresh forever. You never log in again.

---

🤖 Built by MIDAS. The empire is self-building.
