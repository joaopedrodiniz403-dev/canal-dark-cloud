"""Download pinned source repositories, never install or execute their code."""
import argparse
import gzip
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path


def entries(lock):
    data = json.loads(Path(lock).read_text())
    if data.get('schema') != 1 or data.get('download_only') is not True:
        raise ValueError('Unsupported lockfile')
    found = set()
    for item in data['upstreams']:
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,70}', item['id']) or item['id'] in found:
            raise ValueError('Invalid/duplicate upstream id')
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', item['repository']):
            raise ValueError('Invalid repository')
        if not re.fullmatch(r'[0-9a-f]{40}', item['revision']):
            raise ValueError('Revision must be a complete commit SHA')
        found.add(item['id'])
    return data['upstreams']


def download(item, destination):
    destination.mkdir(parents=True, exist_ok=True)
    checkout = destination / 'checkout'
    if checkout.exists():
        raise ValueError('Checkout already exists; use a fresh destination')
    checkout.mkdir()
    env = dict(os.environ, GIT_LFS_SKIP_SMUDGE='1', GIT_TERMINAL_PROMPT='0')
    def git(*args, capture=True):
        return subprocess.run(['git', '-C', str(checkout), *args], check=True, env=env,
                              capture_output=capture, text=capture, timeout=600)
    git('init')
    git('remote', 'add', 'origin', 'https://github.com/' + item['repository'] + '.git')
    git('fetch', '--depth', '1', '--no-tags', 'origin', item['revision'])
    git('checkout', '--detach', 'FETCH_HEAD')
    actual = git('rev-parse', 'HEAD').stdout.strip()
    if actual != item['revision']:
        raise ValueError('Revision mismatch')
    archive = destination / (item['id'] + '.tar.gz')
    # Preserve the upstream tree and licenses. No setup/install script is invoked.
    with gzip.open(archive, 'wb') as compressed:
        proc = subprocess.Popen(['git', '-C', str(checkout), 'archive', '--format=tar', 'HEAD'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        for block in iter(lambda: proc.stdout.read(1024*1024), b''):
            compressed.write(block)
        error = proc.stderr.read()
        if proc.wait() != 0:
            raise RuntimeError(error.decode(errors='replace')[-1000:])
    h = hashlib.sha256()
    with archive.open('rb') as file:
        for block in iter(lambda: file.read(1024*1024), b''):
            h.update(block)
    report = {**item, 'status': 'DOWNLOADED', 'archive': archive.name,
              'archive_sha256': h.hexdigest(), 'bytes': archive.stat().st_size,
              'installed': False, 'executed': False,
              'notes': 'Submodule and Git LFS payloads are not recursively fetched; source tree and pointers are preserved.'}
    (destination/'download-report.json').write_text(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', type=Path, default=Path('agent/upstreams.lock.json'))
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--id')
    parser.add_argument('--output', type=Path, default=Path('work/upstreams'))
    args = parser.parse_args()
    items = entries(args.lock)
    if args.list:
        print(json.dumps({'include': items}))
        return
    selected = [x for x in items if args.id is None or x['id'] == args.id]
    if not selected:
        parser.error('Unknown repository id')
    for item in selected:
        print(json.dumps(download(item, args.output/item['id'])))


if __name__ == '__main__':
    main()
