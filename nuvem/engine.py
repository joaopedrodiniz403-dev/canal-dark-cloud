"""Offline cut engine. Editorial scores are estimates; approval is always human."""
import argparse
import array
import hashlib
import json
import math
import re
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

VERSION = 'cuts-v2'

def run(args, timeout=900):
    p = subprocess.run([str(a) for a in args], capture_output=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(p.stderr.decode(errors='replace')[-3000:])
    return p


def probe(path):
    return json.loads(run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', path]).stdout)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def local_file(root, name):
    p = (root / name).resolve()
    if not p.is_relative_to(root.resolve()) or not p.is_file():
        raise ValueError('Arquivo deve existir dentro de media/authorized (sem symlink externo)')
    return p


def reject_test_source(source, transcription=None):
    backend = str((transcription or {}).get('backend', '')).casefold()
    if source.get('test_only') is True or 'synthetic' in backend or 'fixture' in backend:
        raise ValueError('TEST_INPUT_REJECTED: material sintético de teste não pode entrar na produção')


def validate_rights(source):
    rights = source.get('rights', {})
    if rights.get('verified') is not True or rights.get('kind') not in {'owned', 'licensed', 'permission'}:
        raise ValueError('Direitos de reutilização não verificados')
    for key in ('reference', 'holder', 'verified_by', 'verified_at'):
        if not isinstance(rights.get(key), str) or not rights[key].strip():
            raise ValueError('Falta evidência de direitos: ' + key)
    return rights


def authorize(source, root):
    # This validates the operator's attestation, not the legal truth of the claim.
    validate_rights(source)
    return local_file(root, source['path'])


def validate_words(data, duration):
    words = data.get('words', [])
    if not isinstance(words, list) or not words:
        raise ValueError('Transcrição sem palavras com timestamps')
    previous = -1.0
    for w in words:
        a, b = float(w['start']), float(w['end'])
        text = w.get('text', '')
        if not all(math.isfinite(x) for x in (a, b)) or not (0 <= a < b <= duration + .1) or a < previous - .02:
            raise ValueError('Timestamps inválidos, sobrepostos ou fora do vídeo')
        if not isinstance(text, str) or not text.strip() or len(text) > 20 or '\n' in text:
            raise ValueError('Palavra inválida ou longa demais para legenda')
        previous = b
    return [{**w, 'start': float(w['start']), 'end': float(w['end'])} for w in words]


def transcribe(path, model='small'):
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise RuntimeError('Instale requirements-cuts.txt ou forneça transcrição word-level verificada') from e
    engine = WhisperModel(model, device='cpu', compute_type='int8', cpu_threads=2)
    segments, info = engine.transcribe(str(path), language='pt', word_timestamps=True, vad_filter=True,
                                       condition_on_previous_text=False)
    return {'backend': 'faster-whisper', 'model': model, 'language': info.language,
            'words': [{'text': w.word.strip(), 'start': w.start, 'end': w.end,
                       'probability': w.probability}
                      for s in segments for w in (s.words or []) if w.word.strip()]}


def sentences(words):
    result, current = [], []
    for i, w in enumerate(words):
        current.append(w)
        gap = words[i+1]['start'] - w['end'] if i+1 < len(words) else 10
        if re.search(r'[.!?…]$', w['text']) or gap > 1.2:
            result.append(current)
            current = []
    if current:
        result.append(current)
    return result


def editorial(words):
    text = ' '.join(w['text'] for w in words)
    lower = text.casefold()
    hook = ' '.join(w['text'] for w in words if w['start'] < words[0]['start'] + 3).casefold()
    duration = words[-1]['end'] - words[0]['start']
    density = len(words) / max(1, duration)
    cues = ('olha', 'como', 'por que', 'imagina', 'ninguém', 'não acredito', 'espera')
    parts = {
        'hook': 18 if any(c in hook for c in cues) or '?' in hook else 6,
        'surprise_humor': 12 if any(c in lower for c in ('risos', 'haha', 'impossível', 'surpresa', 'não acredito')) else 0,
        'context_proxy': 14 if len(sentences(words)) >= 3 else 4,
        'reaction_proxy': min(8, text.count('!') * 4),
        'pace': 14 if 1.4 <= density <= 3.8 else 4,
        'closure_proxy': 10 if re.search(r'[.!?…]$', words[-1]['text']) else 0,
    }
    # Originality, visual interest and historical performance are unknown here.
    return {'score': sum(parts.values()), 'components': parts,
            'unknown': ['originality', 'audience_interest', 'historical_performance', 'semantic_coherence'],
            'kind': 'editorial_heuristic_not_virality_prediction'}


def candidates(words, minimum=12, maximum=59):
    sents = sentences(words)
    found = []
    for i in range(len(sents)):
        chosen = []
        for sentence in sents[i:]:
            chosen += sentence
            duration = chosen[-1]['end'] - chosen[0]['start'] + .3
            if duration > maximum:
                break
            if duration >= minimum:
                item = {'start': max(0, chosen[0]['start'] - .12),
                        'end': chosen[-1]['end'] + .18, 'words': list(chosen),
                        'editorial': editorial(chosen)}
                found.append(item)
    return sorted(found, key=lambda c: (-c['editorial']['score'], c['start']))


def timeline(words, start, end):
    """Remove only middle of long inter-word gaps; retain context and breath handles."""
    spans, cursor = [], start
    for left, right in zip(words, words[1:]):
        if right['start'] - left['end'] > 1.5:
            cut_end = left['end'] + .25
            if cut_end > cursor:
                spans.append((cursor, cut_end))
            cursor = right['start'] - .25
    if cursor < end:
        spans.append((cursor, end))
    mapped, offset = [], 0.0
    for a, b in spans:
        for w in words:
            if a <= w['start'] and w['end'] <= b + .001:
                mapped.append({**w, 'start': offset + w['start'] - a, 'end': offset + w['end'] - a})
        offset += b-a
    return spans, mapped


def ass_time(t):
    cs = round(t * 100)
    return f'{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}'


def ass_escape(s):
    return s.replace('\\', '／').replace('{', '(').replace('}', ')').replace('\n', ' ')


def captions(words, path):
    head = '''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,64,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,4,1,2,110,180,400,1
Style: Brand,DejaVu Sans,30,&H00E5B5FF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,2,0,8,80,160,180,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    events = []
    # Three short words per screen, each active word highlighted on its true interval.
    groups, group = [], []
    for w in words:
        if group and (len(group) >= 3 or sum(len(x['text'])+1 for x in group)+len(w['text']) > 20
                      or w['start'] - group[-1]['end'] > .8):
            groups.append(group)
            group = []
        group.append(w)
    if group:
        groups.append(group)
    for group in groups:
        for i, w in enumerate(group):
            text = ' '.join((r'{\c&H00FFFF&}' + ass_escape(x['text']) + r'{\c&HFFFFFF&}')
                            if j == i else ass_escape(x['text']) for j, x in enumerate(group))
            events.append(f"Dialogue: 1,{ass_time(w['start'])},{ass_time(w['end'])},Default,,0,0,0,,{text}")
    end = words[-1]['end'] + .1
    events.append(f'Dialogue: 0,0:00:00.00,{ass_time(end)},Brand,,0,0,0,,NUVEM ESCURA')
    Path(path).write_text(head + '\n'.join(events) + '\n', encoding='utf-8')
    return len(groups)


def render(source, spans, words, work, output, layout='contain'):
    """Keep the complete landscape scene by default; explicit ROI is a future feature."""
    count = captions(words, work / 'captions.ass')
    filters = []
    for i, (a, b) in enumerate(spans):
        filters += [f'[0:v]trim=start={a:.4f}:end={b:.4f},setpts=PTS-STARTPTS[v{i}]',
                    f'[0:a]atrim=start={a:.4f}:end={b:.4f},asetpts=PTS-STARTPTS[a{i}]']
    inputs = ''.join(f'[v{i}][a{i}]' for i in range(len(spans)))
    filters.append(f'{inputs}concat=n={len(spans)}:v=1:a=1[v][a]')
    if layout == 'center':
        filters.append('[v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[vertical]')
    else:
        filters += ['[v]split[bg][fg]',
                    '[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:2[blur]',
                    '[fg]scale=1080:1920:force_original_aspect_ratio=decrease[full]',
                    '[blur][full]overlay=(W-w)/2:(H-h)/2,setsar=1[vertical]']
    filters += ["[vertical]fps=30,subtitles=captions.ass,format=yuv420p[outv]",
                '[a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[outa]']
    (work / 'render.ffscript').write_text(';\n'.join(filters), encoding='utf-8')
    # cwd makes filter paths independent from user-provided filenames and escaping.
    args = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-threads', '2',
            '-i', str(source.resolve()), '-filter_complex_threads', '1', '-filter_complex_script', 'render.ffscript',
            '-map', '[outv]', '-map', '[outa]', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21',
            '-threads', '2', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', str(output.resolve())]
    p = subprocess.run(args, cwd=work, capture_output=True, timeout=1200)
    (work / 'ffmpeg.log').write_bytes(p.stderr)
    if p.returncode:
        raise RuntimeError(p.stderr.decode(errors='replace')[-2500:])
    return count


def qa(path, words, expected):
    data = probe(path)
    v = next(s for s in data['streams'] if s['codec_type'] == 'video')
    audio = next((s for s in data['streams'] if s['codec_type'] == 'audio'), None)
    duration = float(data['format']['duration'])
    # Decode entire result, then measure actual samples (not just container metadata).
    pcm = run(['ffmpeg', '-v', 'error', '-i', path, '-vn', '-ac', '1', '-ar', '16000', '-f', 'f32le', '-']).stdout
    samples = array.array('f')
    samples.frombytes(pcm)
    rms = math.sqrt(sum(x*x for x in samples) / max(1, len(samples)))
    rms_db = 20 * math.log10(max(rms, 1e-12))
    clipping = sum(abs(x) >= .999 for x in samples) / max(1, len(samples))
    visual = run(['ffmpeg', '-hide_banner', '-i', path, '-vf',
                  'freezedetect=n=-50dB:d=3,blackdetect=d=1:pix_th=0.05', '-an', '-f', 'null', '-']).stderr.decode(errors='replace')
    checks = {
        'vertical_1080x1920': (v['width'], v['height']) == (1080, 1920),
        'duration': 12 <= duration <= 59.2 and abs(duration-expected) < .3,
        'audio_present': audio is not None and bool(samples),
        'audio_audible': -38 <= rms_db <= -8,
        'audio_not_clipped': clipping < .001,
        'captions_in_bounds': bool(words) and all(0 <= w['start'] < w['end'] <= duration+.05 for w in words),
        'no_long_freeze': 'freeze_start:' not in visual,
        'no_black_interval': 'black_start:' not in visual,
    }
    return {'passed': all(checks.values()), 'scope': 'technical_only', 'editorial_approved': False, 'publication_approved': False, 'checks': checks, 'duration': duration,
            'audio_rms_dbfs': round(rms_db, 2), 'clipped_sample_fraction': clipping,
            'limitations': ['ASR accuracy and meaning require listening', 'No semantic or legal approval',
                            'Freeze/black detection is a conservative technical gate']}


def content_key(words):
    return hashlib.sha256(re.sub(r'\W+', '', ' '.join(w['text'] for w in words).casefold()).encode()).hexdigest()


def overlaps(a, b):
    intersection = max(0, min(a['end'], b['end']) - max(a['start'], b['start']))
    return intersection / min(a['end']-a['start'], b['end']-b['start']) > .3


def produce(root, manifest, output, state, limit=5, min_score=55, model='small', allow_internal_test=False):
    output.mkdir(parents=True, exist_ok=True)
    state.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(state)
    db.execute('CREATE TABLE IF NOT EXISTS produced (id TEXT PRIMARY KEY, content TEXT UNIQUE, day TEXT, report TEXT)')
    day = datetime.now(ZoneInfo('America/Sao_Paulo')).date().isoformat()
    budget = max(0, min(5, limit) - db.execute('SELECT count(*) FROM produced WHERE day=?', (day,)).fetchone()[0])
    report = {'version': VERSION, 'generated_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat(),
              'publication_enabled': False, 'editorial_approved': False, 'ready_for_review': 0, 'internal_test_count': 0, 'items': [], 'sources': [], 'produced': 0}
    pool = []
    for src in manifest.get('sources', []):
        entry = {'path': src.get('path'), 'status': 'BLOCKED'}
        try:
            if not allow_internal_test:
                reject_test_source(src)
            path = authorize(src, root)
            data = probe(path)
            duration = float(data['format']['duration'])
            if not any(s['codec_type'] == 'audio' for s in data['streams']):
                raise ValueError('Fonte sem áudio')
            sha = digest(path)
            cache = output / 'transcripts' / (sha + '.json')
            if src.get('transcript'):
                transcription = json.loads(local_file(root, src['transcript']).read_text(encoding='utf-8'))
            elif cache.exists():
                transcription = json.loads(cache.read_text(encoding='utf-8'))
            else:
                transcription = transcribe(path, model)
            if not allow_internal_test:
                reject_test_source(src, transcription)
            words = validate_words(transcription, duration)
            save(cache, transcription)
            proposed = candidates(words)
            entry.update(status='ANALYZED', source_sha256=sha, candidate_count=len(proposed),
                         transcript_backend=transcription.get('backend', 'supplied'))
            for c in proposed:
                c.update(source=path, source_sha=sha, rights=src['rights'], layout=src.get('layout', 'contain'),
                         source_duration=duration, test_only=src.get('test_only') is True)
                pool.append(c)
        except Exception as e:
            entry['reason'] = str(e)
        report['sources'].append(entry)
    selected = []
    previous_cuts = [json.loads(row[0]) for row in db.execute('SELECT report FROM produced')]
    for c in sorted(pool, key=lambda x: -x['editorial']['score']):
        if report['produced'] >= budget:
            break
        if c['editorial']['score'] < min_score or any(c['source_sha'] == s['source_sha'] and overlaps(c, s) for s in selected):
            continue
        if any(old.get('source_sha256') == c['source_sha'] and overlaps(c, {'start': old['source_interval'][0], 'end': old['source_interval'][1]}) for old in previous_cuts):
            continue
        key = hashlib.sha256(f"{VERSION}:{c['source_sha']}:{c['start']:.3f}:{c['end']:.3f}".encode()).hexdigest()[:20]
        content = content_key(c['words'])
        if db.execute('SELECT 1 FROM produced WHERE id=? OR content=?', (key, content)).fetchone():
            continue
        item = {'id': key, 'status': 'FAILED', 'editorial': c['editorial'], 'rights': c['rights'],
                'source_sha256': c['source_sha'], 'source_interval': [c['start'], c['end']],
                'test_only': c['test_only'], 'editorial_approved': False, 'publication_approved': False}
        work = output / key
        work.mkdir(exist_ok=True)
        try:
            c['end'] = min(c['end'], c['source_duration'])
            spans, mapped = timeline(c['words'], c['start'], c['end'])
            item['timeline'] = spans
            save(work / 'words.json', {'words': mapped})
            dest = work / 'short.mp4'
            item['caption_groups'] = render(c['source'], spans, mapped, work, dest, c['layout'])
            quality = qa(dest, mapped, sum(b-a for a, b in spans))
            item.update(quality=quality, video=f'{key}/short.mp4', video_sha256=digest(dest))
            item['title'] = ' '.join(w['text'] for w in c['words'][:12])[:90]
            item['description'] = f"Nuvem Escura. Fonte autorizada: {c['rights']['holder']}. #Shorts #NuvemEscura"
            item['editorial_review'] = {'required': True, 'checks': ['contexto e conclusão', 'gancho',
                'legendas versus fala', 'enquadramento', 'título fiel', 'direitos e originalidade', 'políticas YouTube']}
            if c['test_only']:
                item['editorial'] = {'score': None, 'reason': 'Internal fixture is not editorial content'}
            item['status'] = ('TECHNICAL_TEST_ONLY' if c['test_only'] else 'PENDING_HUMAN_REVIEW') if quality['passed'] else 'REJECTED_TECHNICAL_QA'
            if quality['passed']:
                db.execute('INSERT INTO produced VALUES (?, ?, ?, ?)', (key, content, day, json.dumps(item)))
                db.commit()
                report['produced'] += 1
                if c['test_only']:
                    report['internal_test_count'] += 1
                else:
                    report['ready_for_review'] += 1
                selected.append(c)
        except Exception as e:
            item['reason'] = str(e)
        save(work / 'report.json', item)
        report['items'].append(item)
    db.close()
    report['status'] = 'REVIEW_REQUIRED' if report['ready_for_review'] else 'INTERNAL_TESTS_ONLY' if report['internal_test_count'] else ('EMPTY_QUEUE' if not manifest.get('sources') else 'NO_APPROVED_OUTPUT')
    save(output / 'review_queue.json', report)
    (output / 'REVIEW.md').write_text('# Fila Nuvem Escura\n\nNenhum vídeo publicado.\n\n' + '\n'.join(
        f"- {x['id']}: {x['status']} — {x.get('video', x.get('reason', ''))}" for x in report['items']), encoding='utf-8')
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--media-root', type=Path, default=Path('media/authorized'))
    p.add_argument('--manifest', type=Path, default=Path('agent/sources.json'))
    p.add_argument('--output', type=Path, default=Path('output/cuts'))
    p.add_argument('--state', type=Path, default=Path('work/state.sqlite'))
    p.add_argument('--limit', type=int, default=5)
    p.add_argument('--min-score', type=int, default=55)
    p.add_argument('--model', default='small')
    args = p.parse_args()
    report = produce(args.media_root.resolve(), json.loads(args.manifest.read_text(encoding='utf-8')),
                     args.output.resolve(), args.state.resolve(), args.limit, args.min_score, args.model)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report['status'] == 'NO_APPROVED_OUTPUT':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
