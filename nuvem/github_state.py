"""Durable, optimistic state storage on a separate GitHub branch, using Actions token."""
import argparse
import base64
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from .engine import save

BRANCH = 'nuvem-state'
FILE = '.nuvem/state.json'


def empty_state():
    return {'schema': 1, 'sources': {}, 'days': {}, 'videos': []}


def validate(state):
    if state.get('schema') != 1 or not isinstance(state.get('sources'), dict) or not isinstance(state.get('days'), dict) or not isinstance(state.get('videos'), list):
        raise ValueError('Invalid durable state; refusing to reset history')
    return state


class GitHubState:
    def __init__(self, repository, token, default_branch='main'):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
            raise ValueError('Invalid GitHub repository')
        self.base = 'https://api.github.com/repos/' + repository
        self.token = token
        self.default_branch = default_branch
        self.file_sha = None

    def api(self, method, path, body=None, missing=False):
        request = urllib.request.Request(self.base + path,
            data=json.dumps(body).encode() if body is not None else None, method=method,
            headers={'Authorization': 'Bearer ' + self.token, 'Accept': 'application/vnd.github+json',
                     'Content-Type': 'application/json', 'X-GitHub-Api-Version': '2022-11-28'})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    return json.load(response)
            except urllib.error.HTTPError as e:
                if e.code == 404 and missing:
                    return None
                if e.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise RuntimeError(f'GitHub durable state HTTP {e.code}; no history reset') from None
            except urllib.error.URLError:
                if attempt == 2:
                    raise RuntimeError('GitHub durable state unavailable; no history reset') from None
            time.sleep(2**attempt)

    def load(self):
        ref = self.api('GET', '/git/ref/heads/' + BRANCH, missing=True)
        if ref is None:
            base = self.api('GET', '/git/ref/heads/' + self.default_branch)
            self.api('POST', '/git/refs', {'ref': 'refs/heads/' + BRANCH, 'sha': base['object']['sha']})
            state = empty_state()
            self.store(state)
            return state
        data = self.api('GET', '/contents/' + FILE + '?ref=' + BRANCH, missing=True)
        if data is None:
            raise RuntimeError('Durable state file missing on existing branch; refusing history reset')
        self.file_sha = data['sha']
        return validate(json.loads(base64.b64decode(data['content'])))

    def store(self, state):
        validate(state)
        payload = {'message': 'Update Nuvem Escura production history', 'branch': BRANCH,
                   'content': base64.b64encode(json.dumps(state, sort_keys=True).encode()).decode()}
        if self.file_sha:
            payload['sha'] = self.file_sha
        result = self.api('PUT', '/contents/' + FILE, payload)
        self.file_sha = result['content']['sha']


def main():
    p = argparse.ArgumentParser()
    p.add_argument('operation', choices=['pull', 'push'])
    p.add_argument('--file', type=Path, default=Path('work/cloud-state.json'))
    p.add_argument('--lease', type=Path, default=Path('work/cloud-state-lease.json'))
    args = p.parse_args()
    token = os.environ.get('GH_TOKEN')
    if not token:
        p.error('GH_TOKEN missing; production must not continue without durable history')
    client = GitHubState(os.environ['GITHUB_REPOSITORY'], token,
                         os.environ.get('DEFAULT_BRANCH', 'main'))
    if args.operation == 'pull':
        state = client.load()
        save(args.file, state)
        save(args.lease, {'sha': client.file_sha})
    else:
        client.file_sha = json.loads(args.lease.read_text())['sha']
        client.store(json.loads(args.file.read_text()))
    print('Durable state ' + args.operation + ' completed')


if __name__ == '__main__':
    main()
