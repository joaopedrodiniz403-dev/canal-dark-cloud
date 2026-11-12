"""Contract tests use doubles; they do not assess real editorial quality."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from nuvem.framing_stage import selected_segment, apply_selected, process_outputs, framing_mode
from nuvem.chopify_backend import execute

class FramingStageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.p=Path(self.tmp.name);self.source=self.p/'source.mp4';self.source.write_bytes(b'unit source')
        self.out=self.p/'out';self.project=self.out/'project';self.project.mkdir(parents=True)
        self.video=self.out/'exports/native.mp4';self.video.parent.mkdir();self.video.write_bytes(b'unit native')
        self.meta={'start':0,'end':20,'score':8.5}
        self.selected=[{'start':0,'end':20,'overall':8.5}]
        self.transcript={'video':str(self.source),'words':[{'word':'fala','start':0,'end':1}]}
        self.write()
        self.record={'path':'source.mp4','rights':{'verified':True,'kind':'owned','reference':'unit',
            'holder':'unit','verified_by':'unit','verified_at':'2026-11-12'}}
    def write(self):
        for path,data in ((self.video.with_suffix('.meta.json'),self.meta),(self.project/'segments.json',self.selected),
                          (self.project/'transcript.json',self.transcript)):
            path.write_text(json.dumps(data))
    def test_rejected_score_cannot_enter_renderer(self):
        self.meta['score']=5.03;self.selected=[];self.write()
        with patch('nuvem.framing_stage.analyze') as analyze:
            result=apply_selected(self.video,self.source,self.project,self.p,self.out/'framing','owned')
        self.assertEqual(result['status'],'REJECTED_FRAMING_INPUT');analyze.assert_not_called()
    def test_no_selected_segment_cannot_enter_renderer(self):
        self.selected=[];self.write()
        with self.assertRaisesRegex(ValueError,'SELECTION_MISMATCH'):selected_segment(self.video,self.source,self.project)
    def test_wrong_source_rejected(self):
        self.transcript['video']=str(self.p/'other.mp4');self.write()
        with self.assertRaisesRegex(ValueError,'SOURCE_MISMATCH'):selected_segment(self.video,self.source,self.project)
    def test_nonfinite_metadata_rejected(self):
        self.meta['score']=float('nan');self.write()
        with self.assertRaisesRegex(ValueError,'INVALID_METADATA'):selected_segment(self.video,self.source,self.project)
    def test_interval_mismatch_rejected(self):
        self.selected[0]['end']=21;self.write()
        with self.assertRaisesRegex(ValueError,'SELECTION_MISMATCH'):selected_segment(self.video,self.source,self.project)
    def test_native_default_never_calls_postprocessor(self):
        with patch('nuvem.chopify_backend.verify_checkout'),patch('nuvem.chopify_backend.subprocess.run',return_value=subprocess.CompletedProcess([],0)),patch('nuvem.chopify_backend.process_outputs') as process:
            result=execute(self.record,self.p,self.p,self.out)
        process.assert_not_called();self.assertEqual(result['outputs'],['exports/native.mp4'])
    def test_invalid_mode_rejected(self):
        with self.assertRaisesRegex(ValueError,'MODE_UNSUPPORTED'):framing_mode('unknown')
    def test_rejected_framing_never_returns_native(self):
        with patch('nuvem.framing_stage.apply_selected',return_value={'status':'REJECTED_FRAMING_UNCERTAINTY'}):
            outputs,result=process_outputs(self.record,self.source,self.out,self.p,['exports/native.mp4'])
        self.assertEqual(outputs,[]);self.assertEqual(result['status'],'FRAMING_REJECTED')
        self.assertEqual(self.video.read_bytes(),b'unit native')
    def test_success_only_queues_new_review_file(self):
        def staged(video,source,project,upstream,work,rights,attribution):
            work.mkdir(parents=True);final=work/'review.mp4';final.write_bytes(b'unit rendered')
            return {'status':'APPLIED_PENDING_HUMAN_REVIEW','output':str(final)}
        with patch('nuvem.framing_stage.apply_selected',side_effect=staged):
            outputs,result=process_outputs(self.record,self.source,self.out,self.p,['exports/native.mp4'])
        self.assertEqual(len(outputs),1);self.assertTrue(outputs[0].startswith('framing/'))
        self.assertFalse(result['editorial_approved']);self.assertFalse(result['publication_approved'])
        self.assertEqual(self.video.read_bytes(),b'unit native')
    def test_processing_failure_is_not_quality_rejection(self):
        with patch('nuvem.framing_stage.apply_selected',return_value={'status':'FAILED','reason':'ffmpeg error'}):
            with self.assertRaisesRegex(RuntimeError,'PROCESSING_FAILED'):
                process_outputs(self.record,self.source,self.out,self.p,['exports/native.mp4'])
        self.assertTrue((self.out/'framing_report.json').exists())
    def test_output_traversal_rejected(self):
        with self.assertRaisesRegex(ValueError,'OUTPUT_PATH_REJECTED'):
            process_outputs(self.record,self.source,self.out,self.p,['../source.mp4'])
    def test_optin_empty_native_result_never_calls_postprocessor(self):
        self.video.unlink();self.record['framing_mode']='preserve_two_faces'
        with patch('nuvem.chopify_backend.verify_checkout'),patch('nuvem.chopify_backend.subprocess.run',return_value=subprocess.CompletedProcess([],0)),patch('nuvem.chopify_backend.process_outputs') as process:
            result=execute(self.record,self.p,self.p,self.out)
        process.assert_not_called();self.assertEqual(result['outputs'],[])
    def run_stage_double(self,quality=True,uncertain=False,render_error=False):
        from types import SimpleNamespace
        from contextlib import ExitStack
        fake=SimpleNamespace(plan_cuts=lambda *a:[(0,20)],remap_words=lambda *a:(self.transcript['words'],20),apply_cuts=lambda *a:None)
        def render(*args):
            if render_error:raise RuntimeError('encoder failed')
            p=args[-2]/'dual-face-NOT-APPROVED.mp4';p.parent.mkdir(parents=True)
            p.write_bytes(b'unit render');p.with_suffix('.srt').write_text('unit captions');return p
        with ExitStack() as stack:
            stack.enter_context(patch.dict('sys.modules',{'tighten':fake}))
            stack.enter_context(patch('nuvem.framing_stage.analyze',return_value=([],1280,720,'unit')))
            stack.enter_context(patch('nuvem.framing_stage.plan_dual',return_value={'status':'UNCERTAIN' if uncertain else 'DUAL_FACE_DIAGNOSTIC'}))
            stack.enter_context(patch('nuvem.framing_stage.coverage',return_value={'face_visibility_ratio':1.0}))
            stack.enter_context(patch('nuvem.framing_stage.render_dual',side_effect=render))
            stack.enter_context(patch('nuvem.framing_stage.qa',return_value={'passed':quality}))
            return apply_selected(self.video,self.source,self.project,self.p,self.out/'framing','owned')
    def test_technical_qa_failure_returns_no_review_output(self):
        r=self.run_stage_double(quality=False)
        self.assertEqual(r['status'],'REJECTED_FRAMING_TECHNICAL_QA');self.assertIsNone(r['output'])
    def test_uncertain_plan_returns_no_review_output(self):
        r=self.run_stage_double(uncertain=True)
        self.assertEqual(r['status'],'REJECTED_FRAMING_UNCERTAINTY');self.assertIsNone(r['output'])
    def test_encoder_failure_preserves_error_status(self):
        r=self.run_stage_double(render_error=True)
        self.assertEqual(r['status'],'FAILED');self.assertIn('encoder failed',r['reason'])
    def test_success_preserves_captions_and_requires_review(self):
        r=self.run_stage_double();self.assertEqual(r['status'],'APPLIED_PENDING_HUMAN_REVIEW')
        p=Path(r['output']);self.assertTrue(p.with_suffix('.srt').exists())
        meta=json.loads(p.with_suffix('.meta.json').read_text())
        self.assertFalse(meta['editorial_approved']);self.assertFalse(meta['publication_approved'])
