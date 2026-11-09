import json
import tempfile
import unittest
from pathlib import Path
from nuvem.chopify_backend import empty_selection_rejection


class SelectionRejectionTests(unittest.TestCase):
    def records(self,path):
        (path/'project').mkdir()
        error='Candidate scores 5.0-5.0. No clips reached 8.0. Lower the minimum score or run this project with --action prepare to review the range.'
        (path/'project/selection.json').write_text(json.dumps({'passing':0,'min_score':8.0}))
        (path/'project/project.json').write_text(json.dumps({'status':'failed','stage':'render','error':error}))
        (path/'project/segments.json').write_text('[]')
        (path/'pipeline.log').write_text('Chopify: '+error)

    def test_explicit_completed_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.records(p)
            self.assertEqual(empty_selection_rejection(p,1)['passing'],0)

    def test_stale_selection_must_not_hide_decoder_failure(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.records(p)
            (p/'pipeline.log').write_text('TypeError: metadata_errors')
            self.assertIsNone(empty_selection_rejection(p,1))

    def test_render_error_or_killed_process_is_not_a_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.records(p)
            self.assertIsNone(empty_selection_rejection(p,-9))
            (p/'project/selection.json').write_text(json.dumps({'passing':1,'min_score':8.0}))
            self.assertIsNone(empty_selection_rejection(p,1))
