#!/usr/bin/env python3
"""
RESEARCHER AGENT - Generates viral hook queue.
Runs at the start of every workflow. Only refills if queue is low.
"""
import os, json, time
from pathlib import Path
import requests

ROOT = Path(__file__).parent.parent
QUEUE = ROOT / "content" / "hook_queue.json"
PUBLISHED = ROOT / "content" / "published.json"
PROMPT_CFG = ROOT / "config" / "prompt_template.json"
MIN_QUEUE = 5

def load_json(p, default):
    if p.exists():
        try: return json.loads(p.read_text())
        except: return default
    return default

def save_json(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))

def groq_chat(prompt, key, model="llama-3.3-70b-versatile"):
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model, "messages":[{"role":"user","content":prompt}],
              "temperature":0.9, "response_format":{"type":"json_object"}},
        timeout=60
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def gemini_chat(prompt, key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
    r = requests.post(url, json={"contents":[{"parts":[{"text":prompt}]}]}, timeout=60)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]

def main():
    queue = load_json(QUEUE, [])
    published = load_json(PUBLISHED, [])
    print(f"Queue size: {len(queue)} | Published total: {len(published)}")

    if len(queue) >= MIN_QUEUE:
        print("Queue healthy. Skipping research.")
        return

    cfg = load_json(PROMPT_CFG, {})
    recent_titles = [p.get("title","") for p in published[-50:]]
    style_notes = cfg.get("style_notes", "")
    patterns = ", ".join(cfg.get("hook_patterns", []))
    niche = cfg.get("niche", "AI Wealth Psychology")

    prompt = f"""You are a viral short-form video hook writer in the "{niche}" niche.

Style: {style_notes}
Use these proven hook patterns: {patterns}.

Recently published (DO NOT repeat themes): {json.dumps(recent_titles[-20:])}

Generate 10 fresh viral hooks. Each is one provocative sentence under 12 words.
Each must include: contrarian or counter-intuitive insight about money, wealth, AI, or mindset.

Return JSON: {{"hooks":[{{"hook":"...", "topic":"...", "hashtags":["..."]}}]}}
"""
    groq_key = os.environ.get("GROQ_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    raw = None
    if groq_key:
        try:
            raw = groq_chat(prompt, groq_key)
        except Exception as e:
            print(f"Groq failed: {e}")
    if not raw and gemini_key:
        raw = gemini_chat(prompt + "\nReturn ONLY valid JSON.", gemini_key)
        # strip markdown fences
        raw = raw.strip().strip("`")
        if raw.startswith("json"): raw = raw[4:].strip()

    if not raw:
        raise SystemExit("No LLM key worked")

    data = json.loads(raw)
    new_hooks = data.get("hooks", [])
    for h in new_hooks:
        h["created_at"] = int(time.time())
    queue.extend(new_hooks)
    save_json(QUEUE, queue)
    print(f"Added {len(new_hooks)} hooks. New queue size: {len(queue)}")

if __name__ == "__main__":
    main()
