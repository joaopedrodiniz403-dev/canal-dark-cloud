import json
import os
import subprocess
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)
TOPICS = json.loads((ROOT / "data/topics.json").read_text(encoding="utf-8"))
index = int(os.environ.get("TOPIC_INDEX", datetime.now(timezone.utc).toordinal())) % len(TOPICS)
topic = TOPICS[index]

def run(args):
    subprocess.run(args, check=True)

def get_duration(path):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True)
    return float(result.stdout.strip())

def scene_image(i, content):
    image = Image.new("RGB", (540, 960), (12 + i * 5, 26, 52))
    draw = ImageDraw.Draw(image)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    title_font = ImageFont.truetype(bold_path, 32)
    body_font = ImageFont.truetype(font_path, 29)
    small_font = ImageFont.truetype(bold_path, 18)
    draw.rounded_rectangle((25, 50, 515, 90), radius=12, fill=(28, 80, 112))
    draw.text((42, 59), "CURIOSIDADES EM 1 MINUTO", font=small_font, fill="white")
    y = 155
    for line in textwrap.wrap(topic["title"], width=23):
        draw.text((35, y), line, font=title_font, fill=(115, 229, 241))
        y += 48
    draw.rounded_rectangle((25, 340, 515, 720), radius=22, fill=(23, 48, 80))
    y = 400
    for line in textwrap.wrap(content, width=28):
        draw.text((43, y), line, font=body_font, fill="white")
        y += 45
    draw.text((35, 840), f"PARTE {i + 1} / {len(topic['scenes'])}", font=small_font, fill=(115, 229, 241))
    path = OUT / f"scene_{i}.png"
    image.save(path)
    return path

parts = []
for i, content in enumerate(topic["scenes"]):
    img = scene_image(i, content)
    wav = OUT / f"voice_{i}.wav"
    run(["espeak-ng", "-v", "pt-br", "-s", "145", "-w", str(wav), content])
    seconds = get_duration(wav) + 0.5
    part = OUT / f"part_{i}.mp4"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-loop", "1", "-framerate", "15", "-i", str(img),
         "-i", str(wav), "-vf", "scale=1080:1920,format=yuv420p",
         "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
         "-r", "15", "-c:a", "aac", "-b:a", "96k",
         "-t", str(round(seconds, 3)), "-shortest", str(part)])
    parts.append(part)
concat = OUT / "concat.txt"
concat.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
video = OUT / "short.mp4"
run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat",
     "-safe", "0", "-i", str(concat), "-c", "copy", str(video)])
seconds = get_duration(video)
probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
    "-show_entries", "stream=width,height", "-of", "csv=p=0", str(video)],
    capture_output=True, text=True, check=True).stdout.strip()
passed = 0 < seconds <= 60 and probe == "1080,1920" and video.stat().st_size > 10000
report = {"title": topic["title"], "duration_seconds": round(seconds, 2),
    "resolution": probe, "source": topic["source"],
    "review_required": True, "status": "READY_FOR_HUMAN_REVIEW" if passed else "FAILED"}
(OUT / "quality_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "metadata.txt").write_text(topic["title"] + " #Shorts\nFonte para revisão: " + topic["source"], encoding="utf-8")
print(json.dumps(report, ensure_ascii=False))
if not passed:
    raise RuntimeError("Video failed technical validation")
