"""Records the live demo (ffmpeg gdigrab) while demo_script.py runs in a maximised console, then merges the
per-step narration (edge-tts) at the logged step timestamps and burns subtitles.
Output: video/Topic12_Live_Demo_24BTRBT013.mp4 (+ .srt).   Gagan N (24BTRBT013)

    python demo/record_demo.py prepare     # synthesise narration, write durations (no recording)
    python demo/record_demo.py record      # record screen + run demo (needs nodes stopped, deployNodes done)
    python demo/record_demo.py merge       # build the final video from the recording
    python demo/record_demo.py test        # 1 test frame of the console layout -> demo/recording/test_frame.png
"""
import ctypes
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC = os.path.join(ROOT, "demo", "recording")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from tts import synth, split_cue, write_srt  # noqa: E402

OUT = os.path.join(ROOT, "video", "Topic12_Live_Demo_24BTRBT013.mp4")
SRT = os.path.join(ROOT, "video", "Topic12_Live_Demo_24BTRBT013.srt")
RAW = os.path.join(REC, "raw.mp4")
RATE = "+5%"
os.makedirs(REC, exist_ok=True)


def work_area():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass
    from ctypes import wintypes
    r = wintypes.RECT()
    ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0)
    w, h = r.right - r.left, r.bottom - r.top
    return r.left, r.top, w - w % 2, h - h % 2


def prepare():
    steps = json.load(open(os.path.join(ROOT, "demo", "narration.json"), encoding="utf-8"))
    durs = {}
    for s in steps:
        d, _ = synth(s["text"], os.path.join(REC, f"narr_{s['step']:02d}.mp3"), RATE)
        durs[s["step"]] = d
        print(f"  step {s['step']:2d}: narration {d:5.1f}s")
    json.dump(durs, open(os.path.join(REC, "narration_durations.json"), "w"), indent=1)
    print(f"  total narration {sum(durs.values()) / 60:.1f} min")


def start_ffmpeg(path, extra=()):
    x, y, w, h = work_area()
    cmd = ["ffmpeg", "-y", "-loglevel", "info", "-f", "gdigrab", "-framerate", "30", "-draw_mouse", "0",
           "-offset_x", str(x), "-offset_y", str(y), "-video_size", f"{w}x{h}", "-i", "desktop", *extra,
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", path]
    log = open(path + ".log", "w")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=log, stdout=subprocess.DEVNULL)
    return proc, log


def ffmpeg_start_epoch(logpath):
    for _ in range(100):
        txt = open(logpath, encoding="utf-8", errors="replace").read()
        m = re.search(r"start: (\d{9,}\.\d+)", txt)
        if m:
            return float(m.group(1))
        time.sleep(0.1)
    raise RuntimeError("could not read gdigrab start time")


def stop_ffmpeg(proc, log):
    try:
        proc.stdin.write(b"q")
        proc.stdin.flush()
    except Exception:
        pass
    proc.wait(timeout=60)
    log.close()


def test():
    frame = os.path.join(REC, "test_frame.mp4")
    con = subprocess.Popen(["conhost.exe", sys.executable, os.path.join(ROOT, "demo", "layout_test.py")],
                           cwd=ROOT, creationflags=subprocess.CREATE_NEW_CONSOLE)
    time.sleep(4)
    ff, log = start_ffmpeg(frame, extra=("-t", "1"))
    ff.wait()
    log.close()
    con.wait()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", frame, "-frames:v", "1",
                    os.path.join(REC, "test_frame.png")], check=True)
    print("  test frame written")


def record():
    assert os.path.exists(os.path.join(REC, "narration_durations.json")), "run prepare first"
    ff, log = start_ffmpeg(RAW)
    t_ff = ffmpeg_start_epoch(RAW + ".log")
    time.sleep(1.0)
    con = subprocess.Popen(["conhost.exe", sys.executable, os.path.join(ROOT, "demo", "demo_script.py")],
                           cwd=ROOT, creationflags=subprocess.CREATE_NEW_CONSOLE)
    con.wait()
    time.sleep(0.5)
    stop_ffmpeg(ff, log)
    json.dump({"ffmpeg_start": t_ff}, open(os.path.join(REC, "capture.json"), "w"))
    print("  recording finished:", RAW)


def merge():
    steps = json.load(open(os.path.join(REC, "steps.json")))
    t_ff = json.load(open(os.path.join(REC, "capture.json")))["ffmpeg_start"]
    texts = {s["step"]: s["text"] for s in json.load(open(os.path.join(ROOT, "demo", "narration.json"), encoding="utf-8"))}
    # trim: start just before the first step banner (console already maximised), end at the script's end
    t0 = steps["steps"][0]["wall"] - t_ff - 0.6
    t1 = steps["end"] - t_ff
    length = t1 - t0
    cues_all, inputs, filt = [], [], []
    for i, s in enumerate(steps["steps"]):
        n = s["step"]
        mp3 = os.path.join(REC, f"narr_{n:02d}.mp3")
        d, cues = synth(texts[n], mp3, RATE)
        at = s["wall"] - t_ff - t0 + 0.4
        inputs += ["-i", mp3]
        filt.append(f"[{i + 1}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={int(at * 1000)}:all=1[n{i}]")
        for a, b, c in cues:
            for x in split_cue(a, b, c):
                cues_all.append((at + x[0], at + x[1], x[2]))
        print(f"  step {n:2d} at {at:6.1f}s  narration {d:4.1f}s")
    k = len(steps["steps"])
    filt.append("".join(f"[n{i}]" for i in range(k)) + f"amix=inputs={k}:normalize=0:dropout_transition=0,"
                f"apad,atrim=0:{length:.3f}[aout]")
    write_srt(cues_all, SRT)
    import shutil
    shutil.copy(SRT, os.path.join(REC, "subs.srt"))
    # terminal is scaled into the top 1800x956 area; subtitles go in the band below it
    style = ("FontName=Segoe UI,FontSize=11,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,"
             "Outline=0.6,Shadow=0,MarginV=5")
    filt.append(f"[0:v]trim={t0:.3f}:{t1:.3f},setpts=PTS-STARTPTS,scale=1800:-2,pad=1920:1080:60:0:black,"
                f"setsar=1,subtitles=subs.srt:force_style='{style}'[vout]")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-stats", "-i", RAW] + inputs + [
        "-filter_complex", ";".join(filt), "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", OUT]
    subprocess.run(cmd, cwd=REC, check=True)
    print(f"  written {OUT}  ({length / 60:.2f} min)")


if __name__ == "__main__":
    {"prepare": prepare, "record": record, "merge": merge, "test": test}[sys.argv[1]]()
