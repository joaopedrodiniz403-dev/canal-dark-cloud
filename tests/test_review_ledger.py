"""Controlled metadata/media doubles, never editorial or publication evidence."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from nuvem.github_state import empty_state,validate,GitHubState
from nuvem.review_ledger import enqueue,decide
from nuvem.engine import digest

class ReviewLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.video=self.root/'video.mp4';self.srt=self.root/'video.srt'
        self.video.write_bytes(b'unit media double');self.srt.write_text('unit captions')
        self.state=empty_state();self.key=enqueue(self.state,self.video,self.srt,'a'*64,'b'*40,'2026-11-15T00:00:00+00:00')
        self.state['videos'].append(self.key)
    def decide(self,**kwargs):
        args=dict(action='approve',reason='CONTENT_REVIEWED',reviewer='human-user',expected_events=0,confirmed=True)
        args.update(kwargs);return decide(self.state,self.key,self.video,self.srt,**args)
    def test_roundtrip_preserves_pending_item(self):
        state=validate(json.loads(json.dumps(self.state)))
        self.assertEqual(state['reviews'][self.key]['status'],'PENDING_HUMAN_REVIEW')
        self.assertFalse(state['reviews'][self.key]['publication_approved'])
    def test_legacy_state_preserves_history_without_inventing_reviews(self):
        state={'schema':1,'sources':{'original':{'day':'2026-11-14'}},'days':{'2026-11-14':5},'videos':['old']}
        self.assertEqual(validate(state),state);self.assertNotIn('reviews',state)
    def test_confirmed_approval_is_editorial_only(self):
        r=self.decide();self.assertEqual(r['status'],'EDITORIAL_APPROVED');self.assertFalse(r['publication_approved'])
        validate(self.state)
    def test_no_implicit_approval(self):
        with self.assertRaisesRegex(ValueError,'ATTESTATION'):self.decide(confirmed=False)
        self.assertEqual(self.state['reviews'][self.key]['events'],[])
    def test_modified_video_or_srt_invalidates_review(self):
        for target in (self.video,self.srt):
            original=target.read_bytes();target.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'HASH_MISMATCH'):self.decide()
            target.write_bytes(original)
        self.assertEqual(self.state['reviews'][self.key]['events'],[])
    def test_rejection_keeps_previous_event(self):
        self.decide();r=self.decide(action='reject',reason='ASR_ERRORS',expected_events=1)
        self.assertEqual(r['status'],'EDITORIAL_REJECTED');self.assertEqual(len(r['events']),2)
        self.assertEqual(r['events'][0]['action'],'approve');validate(self.state)
    def test_stale_event_count_rejected(self):
        self.decide()
        with self.assertRaisesRegex(ValueError,'STALE'):self.decide()
    def test_corrupt_status_or_publication_flag_cannot_be_stored(self):
        for field,value in [('publication_approved',True),('status','EDITORIAL_APPROVED'),('srt_sha256','wrong')]:
            state=copy.deepcopy(self.state);state['reviews'][self.key][field]=value
            with self.assertRaises(ValueError):validate(state)
    def test_unknown_review_fields_block_private_data(self):
        self.state['reviews'][self.key]['signed_url']='https://example.invalid/private'
        with self.assertRaises(ValueError):validate(self.state)
    def test_existing_hash_binding_cannot_be_replaced(self):
        self.srt.write_text('changed')
        with self.assertRaisesRegex(ValueError,'BINDING_CONFLICT'):
            enqueue(self.state,self.video,self.srt,'a'*64,'b'*40,'2026-11-15T00:00:00+00:00')
    def test_unknown_hash_and_invalid_actor_do_not_mutate(self):
        with self.assertRaisesRegex(ValueError,'UNKNOWN'):
            decide(self.state,'c'*64,self.video,self.srt,'approve','CONTENT_REVIEWED','human',0,True)
        with self.assertRaisesRegex(ValueError,'REVIEWER'):self.decide(reviewer='email@example.invalid')
        self.assertEqual(self.state['reviews'][self.key]['events'],[])
    def test_github_storage_preserves_reviews_and_lease(self):
        import base64
        from unittest.mock import patch
        client=GitHubState('owner/repo','unit-not-a-token');client.file_sha='lease-before'
        with patch.object(client,'api',return_value={'content':{'sha':'lease-after'}}) as api:
            client.store(self.state);payload=api.call_args.args[2]
            self.assertEqual(payload['sha'],'lease-before')
            self.assertEqual(json.loads(base64.b64decode(payload['content']))['reviews'],self.state['reviews'])

    def test_missing_srt_cannot_leave_pending_item_or_consume_budget(self):
        from unittest.mock import patch
        from tests.test_cloud import source_file
        from nuvem.cloud_cycle import cycle
        source=source_file(self.root,'source.mp4');state=empty_state()
        def backend(src,root,upstream,output,**kwargs):
            output.mkdir(parents=True);(output/'clip.mp4').write_bytes(b'unit output without subtitle')
            return {'outputs':['clip.mp4']}
        with patch('nuvem.cloud_cycle.probe',return_value={'format':{'duration':'20'}}):
            report=cycle(self.root,{'sources':[source]},self.root,self.root/'cycle',state,runner=backend,inspector=lambda *a:{'passed':True})
        self.assertEqual(report['sources'][0]['status'],'FAILED')
        self.assertEqual(report['items'],[]);self.assertEqual(report['remaining_daily_budget'],5)
        self.assertEqual(state['reviews'],{});self.assertEqual(state['videos'],[])
