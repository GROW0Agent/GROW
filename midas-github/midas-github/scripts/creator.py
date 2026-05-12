#!/usr/bin/env python3
"""
CREATOR AGENT - Pulls next hook, produces ready-to-post MP4.
Outputs: content/output/video.mp4 + content/output/metadata.json
"""
import os, json, re, subprocess, asyncio, random, tempfile
from pathlib import Path
import requests
import edge_tts

ROOT = Path(__file__).parent.parent
QUEUE = ROOT / "content" / "hook_queue.json"
PUBLISHED = ROOT / "content" / "published.json"
PROMPT_CFG = ROOT / "config" / "prompt_template.json"
OUT_DIR = ROOT / "content" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def load_json(p, d):
    return json.loads(p.read_text()) if p.exists() else d
def save_json(p, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, indent=2))

def groq_chat(prompt, key, model="llama-3.3-70b-versatile", json_mode=True):
    body = {"model": model, "messages":[{"role":"user","content":prompt}], "temperature":0.85}
    if json_mode: body["response_format"] = {"type":"json_object"}
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"}, json=body, timeout=90)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

async def tts_to_mp3(text, voice, out_path):
    communicate = edge_tts.Communicate(text=text, voice=voice, rate="+8%")
    await communicate.save(str(out_path))

def fetch_pexels_clips(keywords, pexels_key, n=5):
    """Returns list of local MP4 paths."""
    clips = []
    for kw in keywords[:n]:
        try:
            r = requests.get("https://api.pexels.com/videos/search",
                headers={"Authorization": pexels_key},
                params={"query": kw, "orientation":"portrait", "size":"medium", "per_page":5},
                timeout=30)
            vids = r.json().get("videos", [])
            if not vids: continue
            chosen = random.choice(vids)
            # pick a vertical file <= 1080p
            files = sorted(chosen.get("video_files", []), key=lambda f: -(f.get("width") or 0))
            mp4_url = None
            for f in files:
                if f.get("file_type") == "video/mp4" and (f.get("height") or 0) >= 720:
                    mp4_url = f["link"]; break
            if not mp4_url and files:
                mp4_url = files[0]["link"]
            if mp4_url:
                local = OUT_DIR / f"clip_{len(clips)}.mp4"
                with requests.get(mp4_url, stream=True, timeout=60) as resp:
                    resp.raise_for_status()
                    with open(local, "wb") as f:
                        for chunk in resp.iter_content(8192): f.write(chunk)
                clips.append(local)
        except Exception as e:
            print(f"Pexels fail for '{kw}': {e}")
    return clips

def extract_keywords(text, max_n=6):
    # crude noun-ish extractor: filter common words
    stop = set("the a an of and to is are was were be been being i you he she it we they them their our your this that these those for on in with by at as from but or not if then so do does did have has had can will would should could about into more most just".split())
    words = re.findall(r"[A-Za-z]{4,}", text.lower())
    seen, out = set(), []
    for w in words:
        if w in stop or w in seen: continue
        seen.add(w); out.append(w)
        if len(out) >= max_n: break
    if not out: out = ["money","success","mindset","future","wealth","city"]
    return out

def build_video(clips, audio_path, captions, out_path):
    """Concat clips, scale to 1080x1920, overlay captions, mix with TTS audio."""
    # 1) trim each clip to 6s, normalize to 1080x1920
    norm = []
    for i, c in enumerate(clips):
        n = OUT_DIR / f"norm_{i}.mp4"
        subprocess.run([
            "ffmpeg","-y","-i",str(c),"-t","6",
            "-vf","scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1",
            "-r","30","-an", str(n)
        ], check=True, stderr=subprocess.DEVNULL)
        norm.append(n)

    concat_list = OUT_DIR / "concat.txt"
    concat_list.write_text("\n".join(f"file '{p}'" for p in norm))
    silent_video = OUT_DIR / "silent.mp4"
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat_list),
                    "-c","copy", str(silent_video)], check=True, stderr=subprocess.DEVNULL)

    # 2) build drawtext caption filter (one centered line per phrase, timed)
    # captions = list of {"text":..., "start":sec, "end":sec}
    filters = []
    for cap in captions:
        txt = cap["text"].replace("'", "\u2019").replace(":", " ")
        filters.append(
            f"drawtext=text='{txt}':fontcolor=white:fontsize=68:"
            f"box=1:boxcolor=black@0.55:boxborderw=18:"
            f"x=(w-text_w)/2:y=h*0.72:"
            f"enable='between(t,{cap['start']:.2f},{cap['end']:.2f})'"
        )
    vf = ",".join(filters) if filters else "null"

    out_no_audio = OUT_DIR / "captioned.mp4"
    subprocess.run(["ffmpeg","-y","-i",str(silent_video),"-vf",vf,
                    "-c:v","libx264","-preset","veryfast","-crf","23",
                    "-pix_fmt","yuv420p", str(out_no_audio)], check=True, stderr=subprocess.DEVNULL)

    # 3) mux TTS audio
    subprocess.run(["ffmpeg","-y","-i",str(out_no_audio),"-i",str(audio_path),
                    "-c:v","copy","-c:a","aac","-b:a","160k","-shortest",
                    str(out_path)], check=True, stderr=subprocess.DEVNULL)

def get_audio_duration(path):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                        "-of","default=noprint_wrappers=1:nokey=1", str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())

def split_into_captions(script, total_duration):
    # split script into ~3-word phrases, time-evenly
    words = script.split()
    chunks = [" ".join(words[i:i+3]) for i in range(0, len(words), 3)]
    if not chunks: return []
    per = total_duration / len(chunks)
    return [{"text": c, "start": i*per, "end": (i+1)*per} for i, c in enumerate(chunks)]

def main():
    queue = load_json(QUEUE, [])
    if not queue:
        raise SystemExit("Hook queue empty — researcher should have filled it")
    cfg = load_json(PROMPT_CFG, {})
    next_hook = queue.pop(0)
    save_json(QUEUE, queue)

    voice = cfg.get("voice", "en-US-GuyNeural")
    niche = cfg.get("niche", "AI Wealth Psychology")
    target_words = cfg.get("script_structure", {}).get("target_word_count", 120)
    style = cfg.get("style_notes", "")

    # 1) script
    script_prompt = f"""You write 30-second viral short-form video scripts in the "{niche}" niche.
Hook to expand: "{next_hook['hook']}"
Style: {style}

Write a {target_words}-word script with this structure:
- HOOK (first 3 seconds, the provided hook, punchy)
- TENSION (10s, set up the conflict/curiosity)
- VALUE (25s, deliver the insight, 1-3 concrete points)
- CTA (5s, "follow for more" variant)

No emojis. No stage directions. Pure spoken script as plain prose.
Return JSON: {{"title":"<70 char YouTube title>","script":"<full script>","hashtags":["#a","#b",...30 niche hashtags]}}"""

    raw = groq_chat(script_prompt, os.environ["GROQ_API_KEY"])
    data = json.loads(raw)
    title = data["title"][:95]
    script = data["script"]
    hashtags = data.get("hashtags", [])[:30]

    # 2) TTS
    audio_path = OUT_DIR / "voice.mp3"
    asyncio.run(tts_to_mp3(script, voice, audio_path))
    duration = get_audio_duration(audio_path)
    print(f"Audio duration: {duration:.1f}s")

    # 3) B-roll
    pexels_key = os.environ["PEXELS_API_KEY"]
    keywords = extract_keywords(next_hook["hook"] + " " + script)
    print(f"B-roll keywords: {keywords}")
    n_clips = max(3, min(8, int(duration / 5) + 1))
    clips = fetch_pexels_clips(keywords, pexels_key, n=n_clips)
    if len(clips) < 2:
        # pad with retries on generic fallback
        fallback = fetch_pexels_clips(["luxury","city","money","future"], pexels_key, n=4)
        clips.extend(fallback)
    if not clips:
        raise SystemExit("No B-roll obtained from Pexels")

    # 4) captions
    captions = split_into_captions(script, duration)

    # 5) build
    out_video = OUT_DIR / "video.mp4"
    build_video(clips, audio_path, captions, out_video)

    # 6) metadata
    affiliate = cfg.get("affiliate_link", "")
    bio = cfg.get("bio_link", "")
    description = f"{next_hook['hook']}\n\n"
    if affiliate: description += f"📌 Recommended: {affiliate}\n"
    if bio: description += f"🔗 Full toolkit: {bio}\n\n"
    description += "Follow for more.\n\n" + " ".join(hashtags)

    metadata = {
        "title": title,
        "description": description,
        "hashtags": hashtags,
        "hook": next_hook["hook"],
        "topic": next_hook.get("topic", ""),
        "video_path": str(out_video.relative_to(ROOT)),
        "duration": duration,
    }
    save_json(OUT_DIR / "metadata.json", metadata)
    print(f"✅ Created: {title}")

if __name__ == "__main__":
    main()
