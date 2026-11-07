"""One bounded production cycle; never approves content or publishes videos."""
import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from .chopify_backend import execute, REVISION
from .engine import authorize, reject_test_source, digest, probe, qa, save
from .github_state import validate
from .media_ingest import materialize


def caption_cues(path):
    text = Path(path).read_text(encoding='utf-8-sig')
    stamps = re.findall(r'(\d\d):(\d\d):(\d\d),(\d{3})\s+-->\s+(\d\d):(\d\d):(\d\d),(\d{3})', text)
    def seconds(values):
        h,m,s,ms = map(int, values)
        return h*3600+m*60+s+ms/1000
    return [{'text': 'caption cue', 'start': seconds(stamp[:4]), 'end': seconds(stamp[4:])} for stamp in stamps]


def cycle(root, manifest, upstream, output, state, runner=execute, inspector=qa):
    validate(state)
    output.mkdir(parents=True, exist_ok=True)
    today = datetime.now(ZoneInfo('America/Sao_Paulo')).date().isoformat()
    remaining = max(0, 5 - int(state['days'].get(today, 0)))
    report = {'generated_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat(),
              'backend': 'chopify', 'revision': REVISION, 'publication_enabled': False,
              'editorial_approved': False, 'ready_for_review': 0, 'sources': [], 'items': [],
              'remaining_daily_budget': remaining,
              'pending_capabilities': ['validated editorial AI reviewer', 'original video generation',
                                       'trend research', 'YouTube OAuth/private upload', 'YouTube real metrics']}
    for source in manifest.get('sources', []):
        entry = {'path': source.get('path'), 'status': 'BLOCKED'}
        report['sources'].append(entry)
        if remaining == 0:
            entry['reason'] = 'DAILY_LIMIT'
            continue
        try:
            reject_test_source(source)
            entry['ingestion'] = materialize(source, root)
            path = authorize(source, root)
            source_hash = digest(path)
            if source_hash in state['sources']:
                entry.update(status='ALREADY_PROCESSED')
                continue
            folder = output / source_hash[:20]
            result = runner(source, root, upstream, folder, max_clips=remaining)
            examined = 0
            accepted = 0
            for relative in result['outputs'][:remaining]:
                video = (folder/relative).resolve()
                if not video.is_relative_to(folder.resolve()) or not video.is_file():
                    raise ValueError('Invalid upstream output path')
                video_hash = digest(video)
                if video_hash in state['videos']:
                    continue
                data = probe(video)
                duration = float(data['format']['duration'])
                cues = caption_cues(video.with_suffix('.srt')) if video.with_suffix('.srt').exists() else []
                quality = inspector(video, cues, duration)
                item = {'video': str(video.relative_to(output.resolve())), 'video_sha256': video_hash,
                        'quality': quality, 'editorial_approved': False, 'publication_approved': False,
                        'status': 'PENDING_HUMAN_REVIEW' if quality['passed'] else 'REJECTED_TECHNICAL_QA'}
                report['items'].append(item)
                examined += 1
                if quality['passed']:
                    accepted += 1
                    report['ready_for_review'] += 1
                    remaining -= 1
                    state['days'][today] = int(state['days'].get(today, 0)) + 1
                    state['videos'].append(video_hash)
            if accepted:
                state['sources'][source_hash] = {'day': today, 'revision': REVISION, 'examined': examined}
            entry.update(status='PROCESSED' if result['outputs'] else 'NO_CANDIDATES')
        except Exception as e:
            entry.update(status='FAILED', reason=str(e))
    report['status'] = 'REVIEW_REQUIRED' if report['ready_for_review'] else 'BLOCKED_NO_AUTHORIZED_MEDIA' if not manifest.get('sources') else 'NO_APPROVED_OUTPUT'
    report['remaining_daily_budget'] = remaining
    save(output/'review_queue.json', report)
    (output/'REVIEW.md').write_text('# Nuvem Escura — revisão\n\nNenhum conteúdo aprovado editorialmente ou publicado.\n\n' +
        '\n'.join(f"- [{x['status']}]({x['video']})" for x in report['items']) +
        ('\n\nBLOQUEADO: nenhuma mídia autorizada cadastrada.' if not manifest.get('sources') else ''), encoding='utf-8')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', type=Path, default=Path('agent/sources.json'))
    p.add_argument('--media-root', type=Path, default=Path('media/authorized'))
    p.add_argument('--upstream', type=Path, default=Path('work/chopify'))
    p.add_argument('--output', type=Path, default=Path('output/cloud'))
    p.add_argument('--state', type=Path, default=Path('work/cloud-state.json'))
    args = p.parse_args()
    state = validate(json.loads(args.state.read_text()))
    try:
        report = cycle(args.media_root.resolve(), json.loads(args.manifest.read_text()), args.upstream.resolve(),
                       args.output.resolve(), state)
    finally:
        save(args.state, state)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if any(x['status'] == 'FAILED' for x in report['sources']):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
