import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from nuvem.asr_benchmark import summarize
from nuvem.chopify_backend import command, execute


def row(model,wer,seconds):
    return {'model':model,'wer':wer,'load_seconds':1.0,'transcribe_seconds':seconds,
            'source_sha256':'a'*64,'reference_sha256':'b'*64,'device':'cpu','compute_type':'int8','cpu_threads':4}


class AsrBenchmarkTests(unittest.TestCase):
    def test_compare_same_source_and_settings_without_changing_default(self):
        result=summarize([row('small',.16,10),row('medium',.1333,27)])
        self.assertEqual(result['lower_wer_model'],'medium')
        self.assertEqual(result['wer_reduction_percentage_points'],2.67)
        self.assertEqual(result['inference_ratio_medium_over_small'],2.7)
        self.assertFalse(result['production_default_changed'])
        self.assertFalse(result['editorial_approval'])

    def test_worse_or_equal_medium_is_not_claimed_as_improvement(self):
        self.assertEqual(summarize([row('small',.1,10),row('medium',.2,20)])['lower_wer_model'],'small')
        self.assertEqual(summarize([row('small',.1,10),row('medium',.1,20)])['lower_wer_model'],'tie')

    def test_different_source_or_settings_cannot_be_compared(self):
        for key,value in [('source_sha256','c'*64),('reference_sha256','c'*64),('cpu_threads',2)]:
            first,second=row('small',.1,10),row('medium',.05,20)
            second[key]=value
            with self.assertRaises(ValueError):summarize([first,second])

    def test_invalid_measurements_or_model_pairs_rejected(self):
        for value in (float('nan'),-1,True):
            first,second=row('small',.1,10),row('medium',.05,20)
            second['wer']=value
            with self.assertRaises(ValueError):summarize([first,second])
        with self.assertRaises(ValueError):summarize([row('small',.1,10),row('small',.1,10)])

    def test_command_preserves_default_and_allows_explicit_medium(self):
        p=Path('/project')
        default=command(p,p/'source.mp4',p,p/'out')
        medium=command(p,p/'source.mp4',p,p/'out',model='medium')
        self.assertEqual(default[default.index('--whisper-model')+1],'small')
        self.assertEqual(medium[medium.index('--whisper-model')+1],'medium')
        self.assertEqual(medium[medium.index('--min-score')+1],'8')

    def test_unsupported_model_blocked_before_backend(self):
        with tempfile.TemporaryDirectory() as d, patch('nuvem.chopify_backend.subprocess.run') as run:
            p=Path(d)
            for model in ('https://example.com/model','large-v3','--arbitrary',{},None):
                with self.assertRaisesRegex(ValueError,'ASR_MODEL_UNSUPPORTED'):
                    execute({'asr_model':model},p,p,p/'out')
            run.assert_not_called()
