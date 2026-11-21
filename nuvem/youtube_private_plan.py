"""Prepare an official private-upload request. No OAuth, HTTP or upload execution."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from .engine import digest,probe
from .github_state import validate

ENDPOINT='https://www.googleapis.com/upload/youtube/v3/videos'
SCOPE='https://www.googleapis.com/auth/youtube.upload'
ROOT=Path(__file__).resolve().parents[1]


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def metadata_body(metadata):
    fields={'title','description','category_id','made_for_kids'}
    if not isinstance(metadata,dict) or set(metadata)!=fields:raise ValueError('INVALID_UPLOAD_METADATA_FIELDS')
    title,description=metadata['title'],metadata['description']
    if not isinstance(title,str) or not 1<=len(title.strip())<=100 or any(c in title for c in '<>\r\n'):
        raise ValueError('INVALID_UPLOAD_TITLE')
    if not isinstance(description,str) or len(description.encode('utf-8'))>5000 or any(c in description for c in '<>'):
        raise ValueError('INVALID_UPLOAD_DESCRIPTION')
    if not isinstance(metadata['category_id'],str) or not re.fullmatch(r'[1-9][0-9]{0,2}',metadata['category_id']):raise ValueError('INVALID_UPLOAD_CATEGORY')
    if type(metadata['made_for_kids']) is not bool:raise ValueError('EXPLICIT_AUDIENCE_REQUIRED')
    return {'snippet':{'title':title.strip(),'description':description,'categoryId':metadata['category_id'],'defaultLanguage':'pt'},
            'status':{'privacyStatus':'private','selfDeclaredMadeForKids':metadata['made_for_kids']}}


def build(state,key,video,srt,metadata,expected_channel_id,metadata_reviewed=False):
    validate(state)
    review=state.get('reviews',{}).get(key)
    if review is None or review['status']!='EDITORIAL_APPROVED':raise ValueError('HUMAN_EDITORIAL_APPROVAL_REQUIRED')
    if metadata_reviewed is not True:raise ValueError('METADATA_REVIEW_ATTESTATION_REQUIRED')
    if not isinstance(expected_channel_id,str) or not re.fullmatch(r'UC[A-Za-z0-9_-]{22}',expected_channel_id):raise ValueError('EXPECTED_CHANNEL_REQUIRED')
    if review['source_sha256'] not in state['sources']:raise ValueError('REVIEW_SOURCE_NOT_IN_HISTORY')
    if video.is_symlink() or srt.is_symlink() or digest(video)!=key or digest(srt)!=review['srt_sha256']:raise ValueError('UPLOAD_MEDIA_HASH_MISMATCH')
    body=metadata_body(metadata)
    media=probe(video)
    streams=media.get('streams',[]);visual=next((x for x in streams if x.get('codec_type')=='video'),{})
    if 'mp4' not in media.get('format',{}).get('format_name','').split(',') or not any(x.get('codec_type')=='audio' for x in streams) or (visual.get('width'),visual.get('height'))!=(1080,1920) or not 15<=float(media.get('format',{}).get('duration',0))<=59.1:
        raise ValueError('PRIVATE_UPLOAD_MEDIA_CONTRACT_REJECTED')
    plan={'schema':1,'operation':'PREPARE_ONLY','upload_executed':False,'publication_approved':False,
        'expected_channel_id':expected_channel_id,'oauth_channel_verified':False,
        'video_sha256':key,'srt_sha256':review['srt_sha256'],'source_sha256':review['source_sha256'],
        'review_events_sha256':canonical_hash(review['events']),'review_event_count':len(review['events']),
        'request':{'method':'POST','endpoint':ENDPOINT,'query':{'part':'snippet,status','uploadType':'resumable','notifySubscribers':'false'},
                   'oauth_scope':SCOPE,'media_content_type':'video/mp4','body':body}}
    plan['plan_id']=canonical_hash(plan)
    return plan


def revalidate(plan,state,video,srt):
    """Invalidate plans after any media, metadata or review-event change."""
    if not isinstance(plan,dict):raise ValueError('INVALID_PRIVATE_UPLOAD_PLAN')
    request=plan.get('request',{});body=request.get('body',{});snippet=body.get('snippet',{});status=body.get('status',{})
    metadata={'title':snippet.get('title'),'description':snippet.get('description'),
              'category_id':snippet.get('categoryId'),'made_for_kids':status.get('selfDeclaredMadeForKids')}
    expected=build(state,plan.get('video_sha256'),video,srt,metadata,plan.get('expected_channel_id'),True)
    if plan!=expected:raise ValueError('PRIVATE_UPLOAD_PLAN_CHANGED_OR_STALE')
    return expected


def write_private(plan,path,root=ROOT):
    allowed=(root/'private/youtube-plans').resolve();destination=path.resolve()
    if not allowed.is_relative_to(root.resolve()) or not destination.is_relative_to(allowed):raise ValueError('PRIVATE_PLAN_OUTPUT_DIRECTORY_REQUIRED')
    destination.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    # A plan contains potentially private titles/descriptions. Never overwrite or follow a file link.
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0)
    fd=os.open(destination,flags,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as file:json.dump(plan,file,ensure_ascii=False,indent=2)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state',type=Path,required=True);p.add_argument('--id',required=True)
    p.add_argument('--video',type=Path,required=True);p.add_argument('--srt',type=Path,required=True)
    p.add_argument('--metadata',type=Path,required=True);p.add_argument('--expected-channel-id',required=True)
    p.add_argument('--confirm-metadata-reviewed',action='store_true')
    args=p.parse_args()
    try:
        state=json.loads(args.state.read_text());metadata=json.loads(args.metadata.read_text())
        plan=build(state,args.id,args.video,args.srt,metadata,args.expected_channel_id,args.confirm_metadata_reviewed)
        write_private(plan,ROOT/'private/youtube-plans'/f"{plan['plan_id']}.json")
    except Exception as error:
        # No titles, paths, bearer tokens or response bodies in diagnostics.
        print(json.dumps({'status':'BLOCKED','error':str(error) if isinstance(error,ValueError) and re.fullmatch(r'[A-Z][A-Z0-9_]+',str(error)) else 'PRIVATE_PLAN_PREPARATION_FAILED','upload_executed':False}))
        raise SystemExit(1)
    print(json.dumps({'status':'PRIVATE_PLAN_PREPARED','plan_id':plan['plan_id'],'upload_executed':False,'publication_approved':False}))


if __name__=='__main__':main()
