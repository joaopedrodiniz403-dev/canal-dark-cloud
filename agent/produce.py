import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from score import score

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "agent"
OUT.mkdir(parents=True, exist_ok=True)
CONFIG = json.loads((ROOT / "agent/config.json").read_text(encoding="utf-8"))
TOPICS = json.loads((ROOT / "agent/topics.json").read_text(encoding="utf-8"))
CLIPS = json.loads((ROOT / "agent/authorized_clips.json").read_text(encoding="utf-8"))["clips"]
MAX = CONFIG["daily_target"]
REPORT = []

def run(cmd):
    subprocess.run(cmd, check=True)

def probe(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True)
    return float(p.stdout.strip())

def render_original(topic, dest):
    from PIL import Image, ImageDraw, ImageFont
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    tmp = dest.parent / (dest.stem + "_parts")
    tmp.mkdir(exist_ok=True)
    parts = []
    for idx, scene in enumerate([topic["hook"]] + topic["scenes"]):
        img = Image.new("RGB", (540, 960), (11, 10 + idx * 4, 32))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((20, 35, 520, 95), radius=14, fill=(77, 25, 122))
        draw.text((42, 50), "NUVEM ESCURA  /  SHORTS", font=ImageFont.truetype(bold_path, 19), fill="white")
        draw.text((34, 165), topic["title"][:27], font=ImageFont.truetype(bold_path, 28), fill=(220, 168, 255))
        font = ImageFont.truetype(font_path, 29)
        import textwrap
        y = 375
        for line in textwrap.wrap(scene, width=27):
            draw.text((38, y), line, font=font, fill="white")
            y += 47
        draw.text((38, 845), f"CENA {idx+1}", font=font, fill=(210, 160, 255))
        png = tmp / f"{idx:02}.png"
        wav = tmp / f"{idx:02}.wav"
        mp4 = tmp / f"{idx:02}.mp4"
        img.save(png)
        run(["espeak-ng", "-v", "pt-br", "-s", "155", "-w", str(wav), scene])
        seconds = probe(wav) + 0.3
        run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-loop", "1", "-framerate", "15",
             "-i", str(png), "-i", str(wav), "-vf", "scale=1080:1920,format=yuv420p",
             "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", "-c:a", "aac",
             "-t", str(seconds), "-shortest", str(mp4)])
        parts.append(mp4)
    concat = tmp / "concat.txt"
    concat.write_text("".join("file '" + p.name + "'\\n" for p in parts))
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat",
         "-safe", "0", "-i", str(concat), "-c", "copy", str(dest)])

def render_clip(clip, dest):
    source = (ROOT / clip["path"]).resolve()
    allowed = (ROOT / "media/authorized").resolve()
    if not source.is_relative_to(allowed) or not source.is_file():
        raise ValueError("Arquivo nao encontrado dentro de media/authorized")
    if not clip.get("permission_reference"):
        raise ValueError("Falta comprovante/referencia da permissao")
    start, end = float(clip["start"]), float(clip["end"])
    if start < 0 or end <= start or end-start > 59:
        raise ValueError("Intervalo invalido")
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", str(start),
         "-i", str(source), "-t", str(end-start), "-vf",
         "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", str(dest)])

def validate(path):
    seconds = probe(path)
    data = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True).stdout.strip()
    return 0 < seconds <= CONFIG["max_duration_seconds"] and data == "1080,1920", round(seconds, 1), data

candidates = []
for t in TOPICS:
    candidates.append({"type":"original", "title":t["title"], "score":score(t), "data":t})
for c in CLIPS:
    if c.get("permission_reference") and c.get("approved_for_reuse") is True:
        candidates.append({"type":"authorized_clip", "title":c.get("title","Corte autorizado"),
            "score":min(100, max(0, int(c.get("editorial_score",65)))), "data":c})
candidates.sort(key=lambda x:x["score"], reverse=True)
for i, item in enumerate(candidates[:MAX], 1):
    dest = OUT / f"short_{i:02}.mp4"
    entry = {"title":item["title"], "type":item["type"], "score":item["score"],
        "video":dest.name, "status":"BLOCKED"}
    try:
        if item["score"] < CONFIG["min_score"]:
            entry["reason"] = "Pontuacao insuficiente"
        else:
            if item["type"] == "original":
                render_original(item["data"], dest)
                entry["source"] = item["data"]["source"]
                entry["note"] = "Roteiro original; voz sintetica simples; revisar fatos, visuais e audio"
            else:
                render_clip(item["data"], dest)
                entry["permission_reference"] = item["data"]["permission_reference"]
                entry["note"] = "Verificar permissao, contexto e transformacao editorial antes de publicar"
            valid, duration, resolution = validate(dest)
            entry.update(duration_seconds=duration, resolution=resolution)
            entry["status"] = "PENDING_HUMAN_REVIEW" if valid else "FAILED_TECHNICAL_QA"
    except Exception as exc:
        entry["status"] = "FAILED"
        entry["reason"] = str(exc)
    REPORT.append(entry)
(OUT / "review_queue.json").write_text(json.dumps({
    "generated_at":datetime.now(timezone.utc).isoformat(),
    "target":MAX, "produced":sum(e["status"]=="PENDING_HUMAN_REVIEW" for e in REPORT),
    "publication_enabled":False, "items":REPORT}, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "README.txt").write_text("REVISAO OBRIGATORIA: videos nao publicados automaticamente.\\nVerifique audio, imagem, direitos, fatos e originalidade antes do upload.\\n", encoding="utf-8")
print(json.dumps(REPORT, ensure_ascii=False, indent=2))
if not any(e["status"]=="PENDING_HUMAN_REVIEW" for e in REPORT):
    sys.exit(1)
