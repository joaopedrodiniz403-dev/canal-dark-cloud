import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import URLError
from nuvem.media_ingest import materialize, checked_url, CheckedRedirect, IngestError
from nuvem.github_state import GitHubState, empty_state

PAYLOAD = b'authorized media transport unit-test bytes'
SECRET_URL = 'https://storage.example.com/video?private_signature=DO_NOT_LEAK'


def source():
    return {'path': 'incoming/video.mp4', 'rights': {'verified': True, 'kind': 'owned',
            'holder': 'test', 'reference': 'test attestation', 'verified_by': 'test', 'verified_at': '2026-11-07'},
            'remote': {'url_env': 'NUVEM_MEDIA_URL_1', 'allowed_hosts': ['storage.example.com'],
                       'sha256': hashlib.sha256(PAYLOAD).hexdigest(), 'max_bytes': 1024}}


class Response(io.BytesIO):
    def __init__(self, body=PAYLOAD, length=None):
        super().__init__(body)
        self.headers = {} if length is None else {'Content-Length': length}
    def geturl(self): return SECRET_URL


class MediaTests(unittest.TestCase):
    def ingest(self, root, src=None, response=None, inspector=None):
        client=Mock()
        client.open.return_value=response if response is not None else Response()
        return materialize(src or source(),root,environ={'NUVEM_MEDIA_URL_1':SECRET_URL},opener=client,
                           inspector=inspector or (lambda _: {'streams':[{'codec_type':'video'},{'codec_type':'audio'}]}))

    def test_download_is_hash_verified_and_secret_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            result=self.ingest(root)
            self.assertEqual((root/'incoming/video.mp4').read_bytes(),PAYLOAD)
            self.assertEqual(result['mode'],'downloaded')
            self.assertNotIn('private_signature',str(result))
            self.assertFalse(list(root.rglob('*.part')))
            # Verified cache doesn't require a still-valid expiring URL.
            cached=materialize(source(),root,environ={})
            self.assertEqual(cached['mode'],'verified_cache')

    def test_unverified_rights_and_test_sources_do_not_download(self):
        for change in ({'rights':{}},{'test_only':True}):
            with tempfile.TemporaryDirectory() as tmp:
                client=Mock()
                with self.assertRaises(ValueError):
                    materialize({**source(),**change},Path(tmp),opener=client)
                client.open.assert_not_called()

    def test_bad_hash_cleans_partial_and_no_final_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            src=source();src['remote']['sha256']='0'*64
            with self.assertRaisesRegex(IngestError,'MEDIA_CHECKSUM_MISMATCH'): self.ingest(root,src)
            self.assertFalse((root/'incoming/video.mp4').exists())
            self.assertFalse(list(root.rglob('*.part')))

    def test_stream_limit_and_declared_limit(self):
        for response in (Response(PAYLOAD*100),Response(PAYLOAD,'9999')):
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaisesRegex(IngestError,'MEDIA_SIZE_REJECTED'):
                    self.ingest(Path(tmp),response=response)
                self.assertFalse(list(Path(tmp).rglob('*.part')))

    def test_secret_errors_are_redacted(self):
        with tempfile.TemporaryDirectory() as tmp:
            client=Mock();client.open.side_effect=URLError(SECRET_URL)
            with self.assertRaises(IngestError) as error:
                materialize(source(),Path(tmp),environ={'NUVEM_MEDIA_URL_1':SECRET_URL},opener=client)
            self.assertEqual(str(error.exception),'MEDIA_FETCH_OR_PROBE_FAILED')
            self.assertNotIn('DO_NOT_LEAK',str(error.exception))

    def test_url_and_redirect_policy(self):
        for url in ('http://storage.example.com/x','https://elsewhere.example/x',
                    'https://user:pass@storage.example.com/x','https://storage.example.com:8443/x',
                    'https://127.0.0.1/x','https://storage.example.com/x#fragment'):
            with self.assertRaises(IngestError): checked_url(url,['storage.example.com'])
        redirect=CheckedRedirect(['storage.example.com'])
        with self.assertRaises(IngestError): redirect.redirect_request(None,None,302,'',{},'https://elsewhere.example/x')

    def test_path_escape_and_missing_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=source();src['path']='../outside.mp4'
            with self.assertRaisesRegex(IngestError,'MEDIA_PATH_REJECTED'): self.ingest(Path(tmp),src)
            with self.assertRaisesRegex(IngestError,'MEDIA_SECRET_MISSING'):
                materialize(source(),Path(tmp),environ={})

    def test_existing_file_is_never_silently_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'incoming').mkdir();target=root/'incoming/video.mp4'
            target.write_bytes(b'human file')
            with self.assertRaisesRegex(IngestError,'MEDIA_EXISTING_FILE_CONFLICT'): self.ingest(root)
            self.assertEqual(target.read_bytes(),b'human file')

    def test_non_media_or_missing_audio_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(IngestError,'MEDIA_AUDIO_VIDEO_REQUIRED'):
                self.ingest(Path(tmp),inspector=lambda _: {'streams':[{'codec_type':'video'}]})
            self.assertFalse((Path(tmp)/'incoming/video.mp4').exists())


class MissingHistoryTests(unittest.TestCase):
    def test_existing_branch_missing_state_blocks_reset(self):
        client=GitHubState('owner/repo','not-a-secret')
        with patch.object(client,'api',side_effect=[{'object':{'sha':'exists'}},None]) as api:
            with self.assertRaisesRegex(RuntimeError,'refusing history reset'): client.load()
            self.assertEqual(api.call_count,2)
            self.assertTrue(all(c.args[0]=='GET' for c in api.call_args_list))

    def test_new_branch_initializes_state_immediately(self):
        client=GitHubState('owner/repo','not-a-secret')
        with patch.object(client,'api',side_effect=[None,{'object':{'sha':'base'}},{},
                         {'content':{'sha':'initialized'}}]) as api:
            self.assertEqual(client.load(),empty_state())
            self.assertEqual(client.file_sha,'initialized')
            self.assertEqual(api.call_args.args[0],'PUT')
