"""Pinned licensed-source contracts; fixtures are not editorial demonstrations."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from nuvem.portuguese_validation import verify_source,obtain,validate

class PortugueseSourceTests(unittest.TestCase):
    def test_wrong_file_blocked_before_upstream_or_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);bad=p/'source.webm';bad.write_bytes(b'unit wrong source')
            with patch('nuvem.portuguese_validation.execute') as process:
                with self.assertRaisesRegex(ValueError,'SOURCE_HASH_MISMATCH'):validate(bad,p,p/'out')
                process.assert_not_called()
    def test_cached_file_must_match_both_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'source.webm';data=b'unit hash fixture';p.write_bytes(data)
            with patch('nuvem.portuguese_validation.SHA256',hashlib.sha256(data).hexdigest()),patch('nuvem.portuguese_validation.SHA1',hashlib.sha1(data).hexdigest()),patch('nuvem.portuguese_validation.urllib.request.urlopen') as network:
                obtain(p);network.assert_not_called()
                with patch('nuvem.portuguese_validation.SHA1','0'*40):
                    with self.assertRaises(ValueError):verify_source(p)
    def test_invalid_cached_file_is_not_overwritten_or_downloaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'source.webm';p.write_bytes(b'unit invalid cached source')
            with patch('nuvem.portuguese_validation.urllib.request.urlopen') as network:
                with self.assertRaises(ValueError):obtain(p)
                network.assert_not_called();self.assertEqual(p.read_bytes(),b'unit invalid cached source')
    def test_download_wrong_hash_never_promoted_and_partial_removed(self):
        import io
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'source.webm'
            with patch('nuvem.portuguese_validation.urllib.request.urlopen',return_value=io.BytesIO(b'unit incorrect download')):
                with self.assertRaises(ValueError):obtain(p)
            self.assertFalse(p.exists());self.assertFalse(p.with_suffix('.partial').exists())
    def test_oversized_download_is_bounded_and_removed(self):
        from unittest.mock import MagicMock
        response=MagicMock();response.__enter__.return_value=response
        response.read.return_value=b'x'*(1024*1024)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'source.webm'
            with patch('nuvem.portuguese_validation.urllib.request.urlopen',return_value=response):
                with self.assertRaisesRegex(ValueError,'SIZE_LIMIT'):obtain(p)
            self.assertEqual(response.read.call_count,61);self.assertFalse(p.exists());self.assertFalse(p.with_suffix('.partial').exists())
    def test_429_without_retry_after_stops_without_loop(self):
        from urllib.error import HTTPError
        from nuvem.portuguese_validation import SourceRateLimited
        with tempfile.TemporaryDirectory() as tmp,patch('nuvem.portuguese_validation.time.sleep') as sleep,patch('nuvem.portuguese_validation.urllib.request.urlopen',side_effect=HTTPError('https://upload.wikimedia.org/',429,'limited',{},None)) as network:
            with self.assertRaises(SourceRateLimited):obtain(Path(tmp)/'source.webm')
            self.assertEqual(network.call_count,1);sleep.assert_not_called()
    def test_429_long_retry_after_does_not_retry_early(self):
        from urllib.error import HTTPError
        from nuvem.portuguese_validation import SourceRateLimited
        with tempfile.TemporaryDirectory() as tmp,patch('nuvem.portuguese_validation.time.sleep') as sleep,patch('nuvem.portuguese_validation.urllib.request.urlopen',side_effect=HTTPError('https://upload.wikimedia.org/',429,'limited',{'Retry-After':'120'},None)):
            with self.assertRaises(SourceRateLimited) as caught:obtain(Path(tmp)/'source.webm')
            self.assertEqual(caught.exception.retry_after_seconds,120);sleep.assert_not_called()
    def test_429_short_retry_after_is_honored_once(self):
        import io
        from urllib.error import HTTPError
        data=b'unit verified source'
        with tempfile.TemporaryDirectory() as tmp,patch('nuvem.portuguese_validation.SHA256',hashlib.sha256(data).hexdigest()),patch('nuvem.portuguese_validation.SHA1',hashlib.sha1(data).hexdigest()),patch('nuvem.portuguese_validation.time.sleep') as sleep,patch('nuvem.portuguese_validation.urllib.request.urlopen',side_effect=[HTTPError('https://upload.wikimedia.org/',429,'limited',{'Retry-After':'1'},None),io.BytesIO(data)]) as network:
            p=Path(tmp)/'source.webm';obtain(p)
            sleep.assert_called_once_with(1);self.assertEqual(network.call_count,2);self.assertEqual(p.read_bytes(),data)
    def test_cli_rate_limit_report_does_not_claim_asr_or_render(self):
        import contextlib,io,json,sys
        from nuvem.portuguese_validation import SourceRateLimited,main
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'out'
            with patch.object(sys,'argv',['diagnostic','--download','--output',str(output)]),patch('nuvem.portuguese_validation.obtain',side_effect=SourceRateLimited()),patch('nuvem.portuguese_validation.validate') as process,contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:main()
            self.assertEqual(caught.exception.code,2);process.assert_not_called()
            r=json.loads((output/'validation.json').read_text())
            self.assertEqual(r['status'],'BLOCKED_SOURCE_RATE_LIMIT');self.assertFalse(r['asr_executed']);self.assertFalse(r['render_executed'])
