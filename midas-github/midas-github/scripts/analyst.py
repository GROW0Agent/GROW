#!/usr/bin/env python3
"""
ANALYST AGENT - Weekly. Pulls YT analytics, asks LLM to rewrite the prompt template.
"""
import os, json, time
from pathlib import Path
import requests

ROOT = Path(__file__).parent.parent
PUBLISHED = ROOT / "content" / "published.json"
PROMPT_CFG = ROOT / "config" / "prompt_template.json"
INSIGHTS = ROOT / "content" / "insights.json"

def yt_stats():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    creds = Credentials(
        token=None, refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube.readonly"])
    yt = build("youtube","v3", credentials=creds)
    pub = json.loads(PUBLISHED.read_text()) if PUBLISHED.exists() else []
    yt_ids = []
    id_to_entry = {}
    for entry in pub[-50:]:
        for r in entry.get("results",[]):
            if r.get("platform")=="youtube" and r.get("id"):
                yt_ids.append(r["id"]); id_to_entry[r["id"]] = entry
    if not yt_ids: return []
    stats = []
    for i in range(0, len(yt_ids), 50):
        batch = yt_ids[i:i+50]
        resp = yt.videos().list(part="statistics,snippet", id=",".join(batch)).execute()
        for item in resp.get("items",[]):
            s = item.get("statistics",{})
            stats.append({
                "id": item["id"],
                "title": item["snippet"]["title"],
                "views": int(s.get("viewCount",0)),
                "likes": int(s.get("likeCount",0)),
                "comments": int(s.get("commentCount",0)),
                "hook": id_to_entry.get(item["id"],{}).get("hook",""),
            })
    return stats

def groq(prompt):
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
        json={"model":"llama-3.3-70b-versatile",
              "messages":[{"role":"user","content":prompt}],
              "temperature":0.4,
              "response_format":{"type":"json_object"}}, timeout=90)
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])

def main():
    stats = yt_stats()
    if not stats:
        print("No YT data yet")
        return
    stats.sort(key=lambda s: -s["views"])
    winners = stats[:max(1,len(stats)//5)]
    losers = stats[-max(1,len(stats)//5):]
    cfg = json.loads(PROMPT_CFG.read_text())

    prompt = f"""You are an analytics expert for viral short-form video.

Current niche: {cfg.get('niche')}
Current style notes: {cfg.get('style_notes')}
Current hook patterns: {cfg.get('hook_patterns')}

WINNERS (top videos):
{json.dumps(winners, indent=2)}

LOSERS (bottom videos):
{json.dumps(losers, indent=2)}

Identify what's working vs failing. Output an updated config as JSON with these EXACT keys:
- "style_notes" (new improved style guidance, 1-3 sentences)
- "hook_patterns" (list of 4-6 patterns to emphasize)
- "rationale" (1-paragraph why)

Be specific. Bias toward what won."""
    out = groq(prompt)
    cfg["style_notes"] = out.get("style_notes", cfg.get("style_notes"))
    cfg["hook_patterns"] = out.get("hook_patterns", cfg.get("hook_patterns"))
    cfg["last_updated"] = time.strftime("%Y-%m-%d")
    PROMPT_CFG.write_text(json.dumps(cfg, indent=2))
    INSIGHTS.write_text(json.dumps({"updated_at":int(time.time()),"rationale":out.get("rationale",""),"sample_winners":winners[:5]}, indent=2))
    print("✅ Analyst updated prompt template")

if __name__ == "__main__":
    main()
