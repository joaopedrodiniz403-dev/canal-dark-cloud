import unittest
from nuvem.caption_audit import audit,parse_srt

class CaptionAuditTests(unittest.TestCase):
    def cue(self,text='Olá, João!',start='00:00:00,000',end='00:00:01,000'):
        return '1\n'+start+' --> '+end+'\n'+text+'\n'
    def test_portuguese_unicode_case_and_punctuation_preserved(self):
        words=[{'word':'OLÁ','start':0,'end':.5},{'word':'Joa\u0303o','start':.5,'end':1}]
        r=audit(self.cue(),2,words);self.assertTrue(r['passed']);self.assertFalse(r['speech_accuracy_verified'])
    def test_missing_word_rejected(self):
        r=audit(self.cue('Olá'),2,[{'word':'Olá João','start':0,'end':1}])
        self.assertEqual(r['reference_match'],'MISMATCH');self.assertFalse(r['passed'])
    def test_accent_change_not_hidden(self):
        r=audit(self.cue('avó'),2,[{'word':'avô','start':0,'end':1}]);self.assertFalse(r['passed'])
    def test_shifted_caption_rejected_even_when_text_matches(self):
        r=audit(self.cue(),3,[{'word':'Olá João','start':1,'end':2}])
        self.assertIn('TRANSCRIPT_TIMING_MISMATCH',[x['code'] for x in r['issues']])
    def test_overlapping_cues_rejected(self):
        text=self.cue()+'\n2\n00:00:00,900 --> 00:00:02,000\nfim\n'
        self.assertFalse(audit(text,3)['passed'])
    def test_rapid_caption_rejected(self):
        self.assertFalse(audit(self.cue('uma frase rápida demais',end='00:00:00,400'),2)['passed'])
    def test_too_brief_caption_rejected(self):
        self.assertFalse(audit(self.cue('Oi',end='00:00:00,100'),2)['passed'])
    def test_long_line_and_three_lines_rejected(self):
        for text in ('x'*43,'um\ndois\ntrês'):
            self.assertFalse(audit(self.cue(text),2)['passed'])
    def test_malformed_block_never_silently_ignored(self):
        for text in ('',self.cue()+'\nmalformed',self.cue().replace('00:00:00,000','00:70:00,000')):
            self.assertFalse(audit(text,2)['passed'])
    def test_negative_or_zero_duration_rejected(self):
        self.assertFalse(audit(self.cue(end='00:00:00,000'),2)['passed'])
        self.assertFalse(audit(self.cue(start='00:00:01,500'),1)['passed'])
    def test_markup_rejected(self):
        self.assertFalse(audit(self.cue('<b>Olá</b>'),2)['passed'])
    def test_no_reference_is_not_speech_verification(self):
        r=audit(self.cue(),2);self.assertTrue(r['passed']);self.assertEqual(r['reference_match'],'NOT_CHECKED')
    def test_bom_and_crlf(self):
        self.assertEqual(len(parse_srt('\ufeff'+self.cue().replace('\n','\r\n'))),1)
    def test_invalid_reference_rejected(self):
        self.assertFalse(audit(self.cue(),2,[{'word':'Olá','start':float('nan'),'end':1}])['passed'])

class CaptionPipelineTests(unittest.TestCase):
    def test_rejected_export_does_not_enter_queue(self):
        import tempfile,json
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import patch
        from nuvem.caption_audit import audit_outputs
        from nuvem.cloud_cycle import cycle
        from nuvem.github_state import empty_state
        from tests.test_cloud import source_file
        words=[{'word':'Olá João','start':0,'end':1}]
        fake=SimpleNamespace(plan_cuts=lambda *a:[],remap_words=lambda *a:(words,20))
        for text,expected in [('Olá João',True),('Olá',False)]:
            with self.subTest(text=text),tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp);out=p/'out';project=out/'project';project.mkdir(parents=True)
                (project/'transcript.json').write_text('{}')
                video=out/'review.mp4';video.write_bytes(b'contract double')
                video.with_suffix('.srt').write_text('1\n00:00:00,000 --> 00:00:01,000\n'+text+'\n')
                with patch.dict('sys.modules',{'tighten':fake}),patch('nuvem.framing_stage.selected_segment',return_value=({'start':0,'end':20},words,{})),patch('nuvem.caption_audit.probe',return_value={'format':{'duration':20}}):
                    outputs,report=audit_outputs(p/'source.mp4',project,p,out,['review.mp4'])
                self.assertEqual(bool(outputs),expected)
                self.assertEqual(report['items'][0]['passed'],expected)
                self.assertFalse(report['editorial_approved'])
                if not expected:
                    source=source_file(p,'input.mp4');state=empty_state()
                    def runner(*args,**kwargs):return {'outputs':outputs,'captions':report,'status':'CAPTIONS_REJECTED'}
                    result=cycle(p,{'sources':[source]},p,p/'cycle',state,runner=runner)
                    self.assertEqual(result['sources'][0]['status'],'CAPTIONS_REJECTED')
                    self.assertEqual(result['sources'][0]['captions'],report)
                    self.assertEqual(result['remaining_daily_budget'],5);self.assertEqual(state['sources'],{})
    def test_backend_does_not_return_caption_rejected_native_exports(self):
        import tempfile,subprocess
        from pathlib import Path
        from unittest.mock import patch
        from nuvem.chopify_backend import execute
        from tests.test_cloud import source_file
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);src=source_file(p,'input.mp4');out=p/'out';(out/'exports').mkdir(parents=True)
            (out/'exports/video.mp4').write_bytes(b'contract double')
            with patch('nuvem.chopify_backend.verify_checkout'),patch('nuvem.chopify_backend.subprocess.run',return_value=subprocess.CompletedProcess([],0)),patch('nuvem.chopify_backend.audit_outputs',return_value=([],{'items':[{'passed':False}]})):
                r=execute(src,p,p,out)
            self.assertEqual(r['status'],'CAPTIONS_REJECTED');self.assertEqual(r['outputs'],[])
