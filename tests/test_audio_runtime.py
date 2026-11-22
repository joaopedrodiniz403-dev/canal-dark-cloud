"""Exercise the exact PyAV decode call that failed with av19; no model/network needed."""
import importlib.util
import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path


@unittest.skipUnless(importlib.util.find_spec('faster_whisper'), 'Optional ASR dependencies not installed')
class AudioRuntimeTests(unittest.TestCase):
    def test_pcm_decode_contract(self):
        from faster_whisper.audio import decode_audio
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'internal-decoder-test.wav'
            with wave.open(str(path),'wb') as file:
                file.setnchannels(1); file.setsampwidth(2); file.setframerate(16000)
                file.writeframes(b'\x00\x00'*4000)
            audio = decode_audio(str(path))
            self.assertEqual(len(audio),4000)
            self.assertEqual(str(audio.dtype),'float32')

    def test_stereo_resample_contract(self):
        from faster_whisper.audio import decode_audio
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'internal-stereo-test.wav'
            with wave.open(str(path),'wb') as file:
                file.setnchannels(2); file.setsampwidth(2); file.setframerate(48000)
                file.writeframes(b''.join(struct.pack('<hh',int(4000*math.sin(i/20)),int(4000*math.sin(i/20))) for i in range(4800)))
            audio = decode_audio(str(path),sampling_rate=16000)
            self.assertLessEqual(abs(len(audio)-1600),1)
            self.assertGreater(float(abs(audio).max()),.01)
