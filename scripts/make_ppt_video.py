"""PPT voice-over video: slide PNGs + edge-tts narration from the speaker notes + crossfades + subtitles.
Output: video/Topic12_PPT_Presentation_24BTRBT013.mp4 (+ .srt).   Gagan N (24BTRBT013)
python scripts/make_ppt_video.py [--rate=+0%]
"""
import os
import shutil
import subprocess
import sys

from pptx import Presentation

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tts import synth, split_cue, write_srt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PPTX = os.path.join(ROOT, "ppt", "Topic12_Secure_P2P_Corda_24BTRBT013.pptx")
RENDER = os.path.join(ROOT, "ppt", "render")
WORK = os.path.join(ROOT, "video", "work", "ppt")
OUT = os.path.join(ROOT, "video", "Topic12_PPT_Presentation_24BTRBT013.mp4")
SRT = os.path.join(ROOT, "video", "Topic12_PPT_Presentation_24BTRBT013.srt")
PAD = 0.7      # silence after each slide's narration
FADE = 0.5     # crossfade length
LEAD = 0.4     # silence before narration on each slide

RATE = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--rate=")), "+0%")


def main():
    os.makedirs(WORK, exist_ok=True)
    prs = Presentation(PPTX)
    notes = [s.notes_slide.notes_text_frame.text.strip() for s in prs.slides]
    slides = [os.path.join(RENDER, f"slide_{i:02d}.png") for i in range(1, len(notes) + 1)]
    assert all(os.path.exists(p) for p in slides), "render the slides first (scripts/render_slides.py)"

    durs, all_cues, starts = [], [], []
    t = 0.0
    for i, text in enumerate(notes, 1):
        mp3 = os.path.join(WORK, f"slide_{i:02d}.mp3")
        d, cues = synth(text, mp3, RATE)
        seg = LEAD + d + PAD
        durs.append(seg)
        starts.append(t)
        for a, b, c in cues:
            for x in split_cue(a, b, c):
                all_cues.append((t + LEAD + x[0], t + LEAD + x[1], x[2]))
        print(f"  slide {i:2d}: narration {d:5.1f}s  segment {seg:5.1f}s  starts at {t:6.1f}s")
        t += seg - FADE
    total = t + FADE
    print(f"  total length {total / 60:.2f} min")
    write_srt(all_cues, SRT)
    shutil.copy(SRT, os.path.join(WORK, "subs.srt"))

    # ---- ffmpeg graph: per slide (image loop + delayed, padded audio) -> xfade / acrossfade chain -> subtitles
    args = ["ffmpeg", "-y", "-loglevel", "error", "-stats"]
    for i, (png, d) in enumerate(zip(slides, durs)):
        args += ["-loop", "1", "-framerate", "30", "-t", f"{d:.3f}", "-i", png]
    for i in range(len(slides)):
        args += ["-i", os.path.join(WORK, f"slide_{i + 1:02d}.mp3")]
    n = len(slides)
    f = []
    for i, d in enumerate(durs):
        f.append(f"[{i}:v]scale=1706:960,pad=1920:1080:107:0:color=0x0B1F3A,setsar=1,format=yuv420p,fps=30[v{i}]")
        f.append(f"[{n + i}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={int(LEAD * 1000)}:all=1,"
                 f"apad,atrim=0:{d:.3f}[a{i}]")
    vprev, aprev = "v0", "a0"
    off = 0.0
    for i in range(1, n):
        off += durs[i - 1] - FADE
        f.append(f"[{vprev}][v{i}]xfade=transition=fade:duration={FADE}:offset={off:.3f}[vx{i}]")
        f.append(f"[{aprev}][a{i}]acrossfade=d={FADE}:c1=tri:c2=tri[ax{i}]")
        vprev, aprev = f"vx{i}", f"ax{i}"
    # subtitles sit in the 120 px band below the slide, so they never cover slide content
    style = ("FontName=Segoe UI,FontSize=11,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,"
             "Outline=0.6,Shadow=0,MarginV=5")
    f.append(f"[{vprev}]subtitles=subs.srt:force_style='{style}'[vout]")
    args += ["-filter_complex", ";".join(f), "-map", "[vout]", "-map", f"[{aprev}]",
             "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage", "-crf", "22", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", OUT]
    script = os.path.join(WORK, "filter.txt")
    open(script, "w").write(";".join(f))
    subprocess.run(args, cwd=WORK, check=True)
    print("  written", OUT)


if __name__ == "__main__":
    main()
