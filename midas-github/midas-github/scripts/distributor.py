#!/usr/bin/env python3
"""
DISTRIBUTOR AGENT - Uploads content/output/video.mp4 to the target platform.
Platform is selected by env TARGET_PLATFORM (youtube/tiktok/instagram/all).
"""
import os, json, time
from pathlib import Path
import requests

ROOT = Path(__file__).parent.parent
OUT = ROOT / "content" / "output"
PUBLISHED = ROOT / "content" / "published.json"

def load_meta():
    return json.loads((OUT / "metadata.json").read_text())

def append_published(entry):
    data = json.loads(PUBLISHED.read_text()) if PUBLISHED.exists() else []
    data.append(entry)
    PUBLISHED.write_text(json.dumps(data, indent=2))

# ---------- YOUTUBE ----------
def upload_youtube(video_path, meta):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube.upload"]
    )
    youtube = build("youtube", "v3", credentials=creds)
    title = meta["title"]
    if "#shorts" not in title.lower():
        title = (title[:90] + " #Shorts").strip()
    body = {
        "snippet": {"title": title, "description": meta["description"], "tags": meta["hashtags"][:15], "categoryId": "27"},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    }
    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = req.next_chunk()
        if status: print(f"YT upload {int(status.progress()*100)}%")
    video_id = response["id"]
    print(f"✅ YouTube: https://youtube.com/shorts/{video_id}")
    return {"platform":"youtube","id":video_id,"url":f"https://youtube.com/shorts/{video_id}"}

# ---------- TIKTOK ----------
def refresh_tiktok_token():
    r = requests.post("https://open.tiktokapis.com/v2/oauth/token/",
        data={
            "client_key": os.environ["TIKTOK_CLIENT_KEY"],
            "client_secret": os.environ["TIKTOK_CLIENT_SECRET"],
            "grant_type": "refresh_token",
            "refresh_token": os.environ["TIKTOK_REFRESH_TOKEN"],
        }, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]

def upload_tiktok(video_path, meta):
    token = os.environ.get("TIKTOK_ACCESS_TOKEN") or refresh_tiktok_token()
    # Try to refresh anyway (access token expires in 24h)
    try:
        token = refresh_tiktok_token()
    except Exception as e:
        print(f"TikTok refresh failed, using stored access token: {e}")

    size = os.path.getsize(video_path)
    init = requests.post("https://open.tiktokapis.com/v2/post/publish/inbox/video/init/",
        headers={"Authorization": f"Bearer {token}", "Content-Type":"application/json"},
        json={"source_info":{"source":"FILE_UPLOAD","video_size":size,"chunk_size":size,"total_chunk_count":1}},
        timeout=30)
    init.raise_for_status()
    j = init.json()["data"]
    upload_url = j["upload_url"]
    publish_id = j["publish_id"]

    with open(video_path, "rb") as f:
        put = requests.put(upload_url,
            headers={"Content-Type":"video/mp4","Content-Range":f"bytes 0-{size-1}/{size}"},
            data=f, timeout=600)
    put.raise_for_status()
    print(f"✅ TikTok: pushed to inbox (publish_id={publish_id})")
    # Note: inbox method requires user to confirm in app on first run after OAuth.
    # For full direct-post, app must be approved for content.posting scope.
    return {"platform":"tiktok","publish_id":publish_id}

# ---------- INSTAGRAM ----------
def upload_instagram(video_path, meta):
    """Instagram Graph API: needs the MP4 hosted at a public URL.
    We commit it to the repo, then use the raw.githubusercontent URL."""
    token = os.environ["IG_ACCESS_TOKEN"]
    ig_user = os.environ["IG_USER_ID"]
    # Public URL of the video committed to the repo
    repo = os.environ.get("GITHUB_REPOSITORY", "GROW0Agent/midas")
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    # The committing step happens AFTER this script -- but for IG we need the URL NOW.
    # Strategy: push the file to a "media" branch via the API before posting.
    public_url = _push_media_and_get_url(video_path, repo, branch)

    caption = (meta["description"][:2100])
    # 1) Create container
    r = requests.post(
        f"https://graph.facebook.com/v20.0/{ig_user}/media",
        params={"media_type":"REELS","video_url":public_url,"caption":caption,"access_token":token},
        timeout=60)
    r.raise_for_status()
    container_id = r.json()["id"]
    # 2) Wait for processing
    for _ in range(40):
        time.sleep(8)
        s = requests.get(f"https://graph.facebook.com/v20.0/{container_id}",
            params={"fields":"status_code","access_token":token}, timeout=30).json()
        if s.get("status_code") == "FINISHED": break
        if s.get("status_code") == "ERROR": raise RuntimeError(f"IG processing failed: {s}")
    # 3) Publish
    pub = requests.post(
        f"https://graph.facebook.com/v20.0/{ig_user}/media_publish",
        params={"creation_id":container_id,"access_token":token}, timeout=60).json()
    media_id = pub.get("id")
    print(f"✅ Instagram Reel posted: {media_id}")
    return {"platform":"instagram","id":media_id}

def _push_media_and_get_url(video_path, repo, branch):
    """Push video to /media in repo via GitHub REST so IG can fetch a public URL."""
    import base64
    gh_token = os.environ.get("GITHUB_TOKEN")
    if not gh_token:
        raise RuntimeError("GITHUB_TOKEN missing — IG needs public file URL")
    fname = f"media/{int(time.time())}_{Path(video_path).name}"
    content = base64.b64encode(Path(video_path).read_bytes()).decode()
    r = requests.put(
        f"https://api.github.com/repos/{repo}/contents/{fname}",
        headers={"Authorization": f"Bearer {gh_token}", "Accept":"application/vnd.github+json"},
        json={"message":f"media upload {fname}","content":content,"branch":branch},
        timeout=120)
    r.raise_for_status()
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{fname}"

# ---------- MAIN ----------
def main():
    meta = load_meta()
    video_path = ROOT / meta["video_path"]
    target = os.environ.get("TARGET_PLATFORM","all").lower()
    print(f"Target: {target} | Video: {video_path}")
    results = []
    tasks = ["youtube","tiktok","instagram"] if target == "all" else [target]
    for plat in tasks:
        try:
            if plat == "youtube":   results.append(upload_youtube(str(video_path), meta))
            elif plat == "tiktok":  results.append(upload_tiktok(str(video_path), meta))
            elif plat == "instagram": results.append(upload_instagram(str(video_path), meta))
        except Exception as e:
            print(f"❌ {plat} failed: {e}")
            results.append({"platform":plat,"error":str(e)})

    append_published({
        "ts": int(time.time()),
        "title": meta["title"],
        "hook": meta["hook"],
        "results": results,
    })

if __name__ == "__main__":
    main()
