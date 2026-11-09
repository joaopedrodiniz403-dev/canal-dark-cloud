"""Explicit, rights-gated integration with a pinned upstream Chopify checkout.

Used by the cloud cycle; real-recording editorial acceptance is still pending.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from .engine import authorize, reject_test_source, save

REPOSITORY = 'https://github.com/mehbul/chopify'
REVISION = 'd576927bf3b764733c97ac1ad324aa9957b0885d'


def verify_checkout(upstream):
    result = subprocess.run(['git', '-C', str(upstream), 'rev-parse', 'HEAD'],
                            capture_output=True, text=True, check=True)
    if result.stdout.strip() != REVISION:
        raise ValueError('Chopify checkout differs from the reviewed, pinned revision')
    dirty = subprocess.run(['git', '-C', str(upstream), 'status', '--porcelain', '--untracked-files=no'],
                           capture_output=True, text=True, check=True)
    if dirty.stdout.strip():
        raise ValueError('Chopify tracked files have local changes')
    if not (upstream/'chopify.py').is_file():
        raise ValueError('Missing upstream CLI')


def command(upstream, source, project, export, max_clips=5):
    # No URLs, paid API, public upload, LLM server or arbitrary CLI injection.
    return [sys.executable, str(upstream/'chopify.py'), str(source),
            '--workdir', str(project), '--out', str(export), '--aspect', '9:16',
            '--min-len', '15', '--max-len', '59', '--max-clips', str(max(1, min(5, int(max_clips)))),
            '--min-score', '8', '--whisper-model', 'small', '--device', 'cpu',
            '--style', 'bold', '--words-per-cue', '3', '--tighten', '--loudnorm',
            '--no-input', '--explain']


def empty_selection_rejection(output, returncode):
    """Recognize only the pinned CLI's explicit completed selection rejection."""
    if returncode != 1:
        return None
    try:
        selection = json.loads((output/'project/selection.json').read_text())
        project = json.loads((output/'project/project.json').read_text())
        segments = json.loads((output/'project/segments.json').read_text())
        error = project.get('error', '')
        log = (output/'pipeline.log').read_text(errors='replace')
        if (type(selection.get('passing')) is int and selection['passing'] == 0
                and selection.get('min_score') == 8.0 and segments == []
                and project.get('stage') == 'render' and project.get('status') == 'failed'
                and error.startswith('Candidate scores ')
                and 'No clips reached 8.0.' in error
                and ('Chopify: ' + error) in log):
            return selection
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return None


def execute(source, root, upstream, output, max_clips=5):
    reject_test_source(source)
    path = authorize(source, root)
    # A supplied fixture transcript must not be used as evidence of a real cut.
    if source.get('transcript'):
        from .engine import local_file
        reject_test_source(source, json.loads(local_file(root, source['transcript']).read_text()))
    verify_checkout(upstream)
    output.mkdir(parents=True, exist_ok=True)
    report = {'backend': REPOSITORY, 'revision': REVISION, 'source': str(path),
              'status': 'FAILED', 'editorial_approved': False, 'publication_approved': False,
              'publication_enabled': False, 'rights': source['rights'], 'outputs': []}
    args = command(upstream, path, output/'project', output/'exports', max_clips)
    report['command'] = args
    try:
        with (output/'pipeline.log').open('w') as log:
            completed = subprocess.run(args, cwd=upstream, stdout=log, stderr=subprocess.STDOUT,
                                       check=False, timeout=3000)
        rejection = empty_selection_rejection(output, completed.returncode)
        if rejection is not None:
            report.update(status='NO_CANDIDATES', reason='EDITORIAL_THRESHOLD', selection=rejection)
            return report
        completed.check_returncode()
        outputs = sorted((output/'exports').glob('*.mp4'))
        report['outputs'] = [str(p.relative_to(output)) for p in outputs]
        report['status'] = 'AWAITING_TECHNICAL_AND_EDITORIAL_REVIEW' if outputs else 'NO_CANDIDATES'
        return report
    except Exception as e:
        report['reason'] = str(e)
        raise
    finally:
        save(output/'upstream_report.json', report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream', type=Path, required=True)
    parser.add_argument('--media-root', type=Path, default=Path('media/authorized'))
    parser.add_argument('--manifest', type=Path, default=Path('agent/sources.json'))
    parser.add_argument('--source-index', type=int, default=0)
    parser.add_argument('--output', type=Path, default=Path('output/chopify'))
    args = parser.parse_args()
    sources = json.loads(args.manifest.read_text())['sources']
    if not 0 <= args.source_index < len(sources):
        parser.error('No authorized source at that index; no demo fallback will be generated')
    print(json.dumps(execute(sources[args.source_index], args.media_root.resolve(),
                             args.upstream.resolve(), args.output.resolve()), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
