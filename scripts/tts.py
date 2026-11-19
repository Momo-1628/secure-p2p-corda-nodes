"""Text-to-speech helper: edge-tts (en-IN-PrabhatNeural) with sentence timings; fallback pyttsx3.
Gagan N (24BTRBT013)."""
import asyncio
import json
import os
import re
import subprocess

VOICE = "en-IN-PrabhatNeural"


def probe_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout.strip()
    return float(out)


async def _edge(text, mp3, rate):
    import edge_tts
    comm = edge_tts.Communicate(text, VOICE, rate=rate, boundary="SentenceBoundary")
    cues = []
    with open(mp3, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] in ("SentenceBoundary", "WordBoundary"):
                start = chunk["offset"] / 1e7
                cues.append([start, start + chunk["duration"] / 1e7, chunk["text"]])
    return cues


def _fallback(text, mp3):
    import pyttsx3
    wav = mp3[:-4] + ".wav"
    eng = pyttsx3.init()
    eng.save_to_file(text, wav)
    eng.runAndWait()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, mp3], check=True)
    os.remove(wav)
    dur = probe_duration(mp3)
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    total = sum(len(s) for s in sentences)
    cues, t = [], 0.0
    for s in sentences:
        d = dur * len(s) / total
        cues.append([t, t + d, s])
        t += d
    return cues


def synth(text, mp3, rate="+0%"):
    """Writes mp3 and returns (duration_seconds, cues[[start,end,text],...]). Cached by text."""
    meta = mp3 + ".json"
    if os.path.exists(mp3) and os.path.exists(meta):
        m = json.load(open(meta, encoding="utf-8"))
        if m.get("text") == text and m.get("rate") == rate:
            return m["duration"], m["cues"]
    try:
        cues = asyncio.run(_edge(text, mp3, rate))
        engine = "edge-tts"
    except Exception as e:  # network problem etc.
        print("  edge-tts failed (%s), falling back to pyttsx3" % e)
        cues = _fallback(text, mp3)
        engine = "pyttsx3"
    dur = probe_duration(mp3)
    json.dump({"text": text, "rate": rate, "duration": dur, "cues": cues, "engine": engine},
              open(meta, "w", encoding="utf-8"))
    return dur, cues


def split_cue(start, end, text, max_chars=84):
    """Split a long sentence into readable subtitle chunks with proportional timing."""
    words = text.split()
    chunks, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 > max_chars and cur:
            chunks.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        chunks.append(cur)
    total = sum(len(c) for c in chunks)
    out, t = [], start
    for c in chunks:
        d = (end - start) * len(c) / total
        out.append((t, t + d, c))
        t += d
    return out


def wrap2(text, width=44):
    """Wrap a subtitle into at most two balanced lines."""
    if len(text) <= width:
        return text
    words = text.split()
    best, line1 = None, ""
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        score = max(len(a), len(b))
        if best is None or score < best:
            best, line1 = score, (a, b)
    return line1[0] + "\n" + line1[1]


def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(cues, path):
    """cues: list of (start, end, text) in absolute seconds."""
    with open(path, "w", encoding="utf-8") as f:
        for i, (a, b, t) in enumerate(cues, 1):
            f.write(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{wrap2(t)}\n\n")
