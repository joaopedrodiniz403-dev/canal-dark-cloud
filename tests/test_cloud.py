import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from nuvem.cloud_cycle import cycle, caption_cues
from nuvem.github_state import GitHubState, empty_state, validate
from tools.download_upstreams import entries


def source_file(root, filename):
    (root/filename).write_bytes(filename.encode())
    return {'path': filename, 'rights': {'verified': True, 'kind': 'owned', 'reference': 'test attestation',
        'holder': 'test', 'verified_by': 'test', 'verified_at': '2026-11-06'}}


class CloudCycleTests(unittest.TestCase):
    def test_no_media_does_not_call_backend(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            with patch('nuvem.cloud_cycle.execute') as run:
                r=cycle(p, {'sources': []}, p, p/'out', empty_state(), runner=run)
            self.assertEqual(r['status'], 'BLOCKED_NO_AUTHORIZED_MEDIA')
            run.assert_not_called()
            self.assertFalse(r['editorial_approved'])

    def test_persistent_budget_and_source_dedup(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            source=source_file(p, 'input.mp4')
            state=empty_state()
            calls=[]
            def backend(src, root, upstream, output, max_clips):
                calls.append(max_clips)
                (output/'exports').mkdir(parents=True)
                for i in range(max_clips):
                    (output/'exports'/f'{i}.mp4').write_bytes(f'video-{i}'.encode())
                    (output/'exports'/f'{i}.srt').write_text('1\n00:00:00,100 --> 00:00:01,000\nhello\n')
                return {'outputs': [f'exports/{i}.mp4' for i in range(max_clips)]}
            with patch('nuvem.cloud_cycle.probe', return_value={'format': {'duration': '20'}}):
                inspector=lambda *args: {'passed': True, 'scope': 'technical_only'}
                r=cycle(p, {'sources': [source]}, p, p/'first', state, backend, inspector)
                self.assertEqual(r['ready_for_review'],5)
                again=cycle(p, {'sources': [source]}, p, p/'again', state, backend, inspector)
                self.assertEqual(again['ready_for_review'],0)
                self.assertEqual(calls,[5])
                self.assertTrue(all(not x['publication_approved'] for x in r['items']))
                # Another day resets budget but must still skip a processed source.
                state['days']={}
                cycle(p, {'sources': [source]}, p, p/'next-day', state, backend, inspector)
                self.assertEqual(calls,[5])

    def test_synthetic_source_never_calls_backend(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            source=source_file(p,'input.mp4')
            source['test_only']=True
            with patch('nuvem.cloud_cycle.execute') as backend:
                r=cycle(p,{'sources':[source]},p,p/'out',empty_state(),runner=backend)
                backend.assert_not_called()
                self.assertEqual(r['sources'][0]['status'],'FAILED')

    def test_corrupt_state_cannot_reset_history(self):
        with self.assertRaises(ValueError):
            validate({'schema':1,'sources':{},'days':{}})

    def test_srt_cue_parsing(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.srt'
            p.write_text('1\n00:00:01,250 --> 00:00:02,500\nhello\n')
            cue=caption_cues(p)[0]
            self.assertEqual((cue['start'],cue['end']),(1.25,2.5))


class DurableStateTests(unittest.TestCase):
    def test_write_preserves_optimistic_lease(self):
        client=GitHubState('owner/repo','test-not-a-real-token')
        client.file_sha='previous-sha'
        with patch.object(client,'api',return_value={'content':{'sha':'new-sha'}}) as api:
            client.store(empty_state())
            self.assertEqual(api.call_args.args[2]['sha'],'previous-sha')
            self.assertEqual(api.call_args.args[2]['branch'],'nuvem-state')

    def test_invalid_lockfile_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'lock.json'
            p.write_text(json.dumps({'schema':1,'download_only':True,'upstreams':[
                {'id':'good','repository':'owner/repo;whoami','revision':'a'*40}]}))
            with self.assertRaises(ValueError): entries(p)

    def test_lockfile_eight_pinned_repositories(self):
        self.assertEqual(len(entries('agent/upstreams.lock.json')),8)
