import tempfile
import unittest
from pathlib import Path
from nuvem.caption_reflow import plan,write
from nuvem.caption_audit import parse_srt,tokens

class ReflowTests(unittest.TestCase):
    def test_regroups_rapid_three_word_caption_without_changing_words(self):
        words=[{'word':t,'start':a,'end':b} for t,a,b in [('Olá',0,.4),('meu',.4,.5),('amigo',.5,.6),('vamos',.6,1.2),('conversar',1.2,2)]]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);r=write(words,2,p/'captions.ass',p/'captions.srt')
            self.assertTrue(r['passed']);c=parse_srt((p/'captions.srt').read_text())
            self.assertEqual(tokens(' '.join(x['text'] for x in c)),tokens(' '.join(x['word'] for x in words)))
            ass=(p/'captions.ass').read_text();self.assertEqual(ass.count('Dialogue:'),len(c))
            for cue in c:self.assertIn(r'\N'.join(cue['text'].splitlines()),ass)
    def test_impossible_speech_is_rejected_without_extending_timestamps(self):
        words=[{'word':'incompreensivelmente','start':0,'end':.1}]
        self.assertEqual(plan(words,1)['status'],'NO_READABLE_PLAN')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            with self.assertRaisesRegex(ValueError,'NO_READABLE'):write(words,1,p/'a.ass',p/'a.srt')
            self.assertFalse((p/'a.ass').exists());self.assertFalse((p/'a.srt').exists())
    def test_long_silence_does_not_join_unrelated_speech(self):
        words=[{'word':'Olá','start':0,'end':.4},{'word':'sim','start':3,'end':3.5}]
        p=plan(words,4);self.assertEqual(len(p['cues']),2)
    def test_invalid_overlap_and_hidden_words_not_silently_dropped(self):
        with self.assertRaises(ValueError):plan([{'word':'a','start':1,'end':2},{'word':'b','start':1.5,'end':3}],4)
        words=[{'word':'fala','start':0,'end':1,'hidden':True}]
        self.assertEqual(plan(words,1)['cues'][0]['text'],'fala')
    def test_ass_control_characters_are_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write([{'word':r'{\pos(0,0)}','start':0,'end':1}],1,p/'a.ass',p/'a.srt')
            self.assertNotIn(r'{\pos(0,0)}',(p/'a.ass').read_text())
