"""Request-planning contracts only; no YouTube service or editorial acceptance."""
import copy
import json
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from nuvem.youtube_private_plan import build,revalidate,write_private,metadata_body
from nuvem.review_ledger import enqueue,decide
from nuvem.github_state import empty_state

class PrivateUploadPlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.video=self.root/'clip.mp4';self.video.write_bytes(b'unit-media-double')
        self.srt=self.root/'clip.srt';self.srt.write_text('unit captions')
        self.state=empty_state();self.key=enqueue(self.state,self.video,self.srt,'a'*64,'b'*40,'2026-11-15T00:00:00+00:00')
        self.state['videos'].append(self.key);self.state['sources']['a'*64]={'day':'2026-11-15'}
        decide(self.state,self.key,self.video,self.srt,'approve','CONTENT_REVIEWED','unit-reviewer',0,True)
        self.metadata={'title':'Título de contrato','description':'Descrição de teste de contrato','category_id':'20','made_for_kids':False}
        self.channel='UC'+'a'*22
        self.probe=patch('nuvem.youtube_private_plan.probe',return_value={'format':{'duration':'20','format_name':'mov,mp4,m4a,3gp,3g2,mj2'},'streams':[{'codec_type':'video','width':1080,'height':1920},{'codec_type':'audio'}]}).start()
        self.addCleanup(patch.stopall)
    def build(self):return build(self.state,self.key,self.video,self.srt,self.metadata,self.channel,True)
    def test_official_private_only_request_and_no_execution(self):
        p=self.build();self.assertEqual(p['request']['body']['status']['privacyStatus'],'private')
        self.assertEqual(p['request']['query']['notifySubscribers'],'false');self.assertFalse(p['upload_executed'])
        self.assertFalse(p['oauth_channel_verified']);self.assertFalse(p['publication_approved'])
        self.assertEqual(revalidate(p,self.state,self.video,self.srt),p)
    def test_pending_or_rejected_review_cannot_plan(self):
        self.state['reviews'][self.key]['events']=[];self.state['reviews'][self.key]['status']='PENDING_HUMAN_REVIEW'
        with self.assertRaisesRegex(ValueError,'APPROVAL_REQUIRED'):self.build()
        decide(self.state,self.key,self.video,self.srt,'reject','ASR_ERRORS','unit-reviewer',0,True)
        with self.assertRaisesRegex(ValueError,'APPROVAL_REQUIRED'):self.build()
    def test_mutated_media_or_subtitles_blocked(self):
        for target in (self.video,self.srt):
            original=target.read_bytes();target.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'HASH_MISMATCH'):self.build()
            target.write_bytes(original)
    def test_public_unlisted_schedule_or_credentials_cannot_enter_metadata(self):
        for field,value in [('privacyStatus','public'),('privacyStatus','unlisted'),('publishAt','2026-11-20T12:00:00Z'),('access_token','unit-not-a-token')]:
            m={**self.metadata,field:value}
            with self.assertRaisesRegex(ValueError,'METADATA_FIELDS'):metadata_body(m)
    def test_tampered_plan_body_or_endpoint_is_invalid(self):
        p=self.build()
        for mutate in (lambda x:x['request']['body']['status'].update(privacyStatus='public'),lambda x:x['request'].update(endpoint='https://example.invalid')):
            bad=copy.deepcopy(p);mutate(bad)
            with self.assertRaisesRegex(ValueError,'CHANGED_OR_STALE'):revalidate(bad,self.state,self.video,self.srt)
    def test_new_decision_invalidates_plan_even_if_approved_again(self):
        p=self.build();decide(self.state,self.key,self.video,self.srt,'approve','CONTENT_REVIEWED','unit-reviewer',1,True)
        with self.assertRaisesRegex(ValueError,'CHANGED_OR_STALE'):revalidate(p,self.state,self.video,self.srt)
    def test_metadata_review_confirmation_required(self):
        with self.assertRaisesRegex(ValueError,'METADATA_REVIEW'):build(self.state,self.key,self.video,self.srt,self.metadata,self.channel)
    def test_audience_and_title_limits(self):
        for change in ({'made_for_kids':'false'},{'title':'x'*101},{'description':'á'*2501}):
            with self.assertRaises(ValueError):metadata_body({**self.metadata,**change})
    def test_media_contract_and_channel_required(self):
        self.probe.return_value['streams'][0]['width']=1920
        with self.assertRaisesRegex(ValueError,'MEDIA_CONTRACT'):self.build()
        with self.assertRaisesRegex(ValueError,'CHANNEL_REQUIRED'):build(self.state,self.key,self.video,self.srt,self.metadata,'wrong',True)
    def test_private_output_permissions_and_no_overwrite(self):
        p=self.build();path=self.root/'private/youtube-plans'/f"{p['plan_id']}.json"
        write_private(p,path,self.root);self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
        with self.assertRaises(FileExistsError):write_private(p,path,self.root)
        with self.assertRaisesRegex(ValueError,'OUTPUT_DIRECTORY'):write_private(p,self.root/'public.json',self.root)
    def test_unknown_or_missing_source_cannot_plan(self):
        self.state['sources']={}
        with self.assertRaisesRegex(ValueError,'SOURCE_NOT_IN_HISTORY'):self.build()
    def test_rejected_revision_blocks_previously_valid_plan(self):
        p=self.build();decide(self.state,self.key,self.video,self.srt,'reject','CONTEXT_INCOMPLETE','unit-reviewer',1,True)
        with self.assertRaisesRegex(ValueError,'APPROVAL_REQUIRED'):revalidate(p,self.state,self.video,self.srt)
    def test_cli_failure_does_not_print_private_paths_or_metadata(self):
        import contextlib,io,sys
        from nuvem.youtube_private_plan import main
        private_name=self.root/'private-title-do-not-log.json'
        stdout=io.StringIO()
        with patch.object(sys,'argv',['planner','--state',str(private_name),'--id',self.key,'--video',str(self.video),'--srt',str(self.srt),'--metadata',str(private_name),'--expected-channel-id',self.channel]),contextlib.redirect_stdout(stdout):
            with self.assertRaises(SystemExit):main()
        self.assertNotIn('private-title-do-not-log',stdout.getvalue())
        self.assertEqual(json.loads(stdout.getvalue())['status'],'BLOCKED')
    def test_private_parent_symlink_cannot_escape_repository(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.root/'private').symlink_to(outside,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'OUTPUT_DIRECTORY'):
                write_private(self.build(),self.root/'private/youtube-plans/plan.json',self.root)
