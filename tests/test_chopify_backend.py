import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from nuvem.chopify_backend import command, execute, REVISION


class ChopifyAdapterTests(unittest.TestCase):
    def test_command_is_local_and_bounded(self):
        args = command(Path('/upstream'), Path('/authorized/source.mp4'), Path('/project'), Path('/exports'))
        self.assertIn('9:16', args)
        self.assertEqual(args[args.index('--max-len')+1], '59')
        self.assertEqual(args[args.index('--max-clips')+1], '5')
        self.assertNotIn('--llm', args)
        self.assertIn('--no-input', args)

    def test_fixture_blocked_before_process(self):
        with tempfile.TemporaryDirectory() as tmp, patch('nuvem.chopify_backend.subprocess.run') as process:
            p = Path(tmp)
            with self.assertRaisesRegex(ValueError, 'TEST_INPUT_REJECTED'):
                execute({'test_only': True}, p, p, p/'out')
            process.assert_not_called()

    def test_rights_blocked_before_process(self):
        with tempfile.TemporaryDirectory() as tmp, patch('nuvem.chopify_backend.subprocess.run') as process:
            p = Path(tmp)
            with self.assertRaises(ValueError):
                execute({'path': 'source.mp4'}, p, p, p/'out')
            process.assert_not_called()

    def test_real_output_discovery_contract(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p/'source.mp4').write_bytes(b'authorized test input')
            (p/'output/exports').mkdir(parents=True)
            (p/'output/exports/real-output.mp4').write_bytes(b'upstream output contract')
            source = {'path': 'source.mp4', 'rights': {'verified': True, 'kind': 'owned',
                'reference': 'test', 'holder': 'test', 'verified_by': 'test', 'verified_at': '2026-11-06'}}
            with patch('nuvem.chopify_backend.verify_checkout'), patch('nuvem.chopify_backend.subprocess.run'):
                result = execute(source, p, p, p/'output', max_clips=2)
            self.assertEqual(result['outputs'], ['exports/real-output.mp4'])
            self.assertFalse(result['editorial_approved'])
