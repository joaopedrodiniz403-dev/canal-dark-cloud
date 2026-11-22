"""Adapter contracts use controlled doubles; real render is a separate licensed diagnostic."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from nuvem.readable_portrait import caption_hooks,process_outputs
from nuvem.engine import digest

class ReadablePortraitTests(unittest.TestCase):
    def test_same_plan_used_for_burned_ass_and_external_srt(self):
        renderer=SimpleNamespace(build_ass=lambda *a:None);captions=SimpleNamespace(write_srt=lambda *a:None)
        original_ass,original_srt=renderer.build_ass,captions.write_srt
        words=[{'word':'fala','start':.2,'end':.3}]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            with caption_hooks(renderer,captions,p) as report:
                renderer.build_ass(words,0,1,p/'_caption.ass',1080,1920)
                captions.write_srt(words,0,1,p/'export.srt',group_size=3)
                self.assertEqual(digest(p/'_caption.ass'),report['ass_sha256'])
                self.assertEqual(digest(p/'export.srt'),report['srt_sha256'])
                self.assertTrue(report['caption_audit']['passed'])
                with self.assertRaisesRegex(ValueError,'TIMELINE_MISMATCH'):
                    captions.write_srt([{'word':'changed','start':.2,'end':.3}],0,1,p/'wrong.srt')
            self.assertIs(renderer.build_ass,original_ass);self.assertIs(captions.write_srt,original_srt)
    def test_functions_restored_after_failed_render(self):
        a=lambda *args:None;b=lambda *args:None
        renderer=SimpleNamespace(build_ass=a);captions=SimpleNamespace(write_srt=b)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                with caption_hooks(renderer,captions,Path(tmp)):raise RuntimeError('unit encoder failure')
        self.assertIs(renderer.build_ass,a);self.assertIs(captions.write_srt,b)
    def test_selector_rejection_blocks_readable_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'exports').mkdir();video=p/'exports/clip.mp4';video.write_bytes(b'unit native')
            with patch('nuvem.readable_portrait.selected_segment',side_effect=ValueError('FRAMING_SELECTOR_REJECTED')),patch('nuvem.readable_portrait.render') as render:
                outputs,report=process_outputs({'rights':{}},p/'source.mp4',p,p,['exports/clip.mp4'])
                render.assert_not_called()
            self.assertEqual(outputs,[]);self.assertEqual(report['status'],'CAPTIONS_REJECTED')
            self.assertEqual(video.read_bytes(),b'unit native')
    def test_infrastructure_failure_is_not_disguised_as_plan_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'exports').mkdir();(p/'exports/clip.mp4').write_bytes(b'unit native')
            with patch('nuvem.readable_portrait.selected_segment',return_value=({'start':0,'end':20},[],{})),patch('nuvem.readable_portrait.probe',return_value={'streams':[{'codec_type':'video','width':1920,'height':1080}]}),patch('nuvem.readable_portrait.render',side_effect=RuntimeError('unit encoder failed')):
                with self.assertRaisesRegex(RuntimeError,'encoder failed'):
                    process_outputs({'rights':{}},p/'source.mp4',p,p,['exports/clip.mp4'])
            self.assertEqual(json.loads((p/'readable_report.json').read_text())['status'],'FAILED')
    def test_no_native_candidate_never_calls_optional_readable_stage(self):
        import subprocess
        from nuvem.chopify_backend import execute
        from tests.test_cloud import source_file
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);source=source_file(p,'source.mp4');source['caption_mode']='readable'
            with patch('nuvem.chopify_backend.verify_checkout'),patch('nuvem.chopify_backend.subprocess.run',return_value=subprocess.CompletedProcess([],0)),patch('nuvem.readable_portrait.process_outputs') as rerender:
                report=execute(source,p,p,p/'out')
            rerender.assert_not_called();self.assertEqual(report['outputs'],[])
