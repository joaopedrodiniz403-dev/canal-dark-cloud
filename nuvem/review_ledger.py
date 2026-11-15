"""Durable human-review metadata; no upload or publication authority."""
import argparse
import json
import re
from datetime import datetime,timezone
from pathlib import Path
from .engine import digest,save

HASH=re.compile(r'[a-f0-9]{64}')
REASONS={'approve':{'CONTENT_REVIEWED'},'reject':{'ASR_ERRORS','CONTEXT_INCOMPLETE','FRAMING','CAPTIONS','RIGHTS_UNVERIFIED','EDITORIAL_REJECTED'}}
FIELDS={'video_sha256','srt_sha256','source_sha256','revision','created_at','status','events','publication_approved'}


def timestamp(value):
    if not isinstance(value,str):raise ValueError('INVALID_REVIEW_TIMESTAMP')
    try:parsed=datetime.fromisoformat(value)
    except ValueError:raise ValueError('INVALID_REVIEW_TIMESTAMP') from None
    if parsed.utcoffset() is None:raise ValueError('INVALID_REVIEW_TIMESTAMP')


def validate_reviews(reviews,videos):
    if not isinstance(reviews,dict):raise ValueError('INVALID_REVIEW_LEDGER')
    for key,item in reviews.items():
        if not isinstance(item,dict) or set(item)!=FIELDS:raise ValueError('INVALID_REVIEW_RECORD')
        if any(not isinstance(item.get(k),str) or not HASH.fullmatch(item[k]) for k in ('video_sha256','srt_sha256','source_sha256')):
            raise ValueError('INVALID_REVIEW_HASH')
        if key!=item['video_sha256'] or key not in videos:raise ValueError('ORPHAN_REVIEW_RECORD')
        if not isinstance(item['revision'],str) or not re.fullmatch(r'[a-f0-9]{40}',item['revision']):raise ValueError('INVALID_REVIEW_REVISION')
        timestamp(item['created_at'])
        if item['publication_approved'] is not False or not isinstance(item['events'],list):raise ValueError('REVIEW_CANNOT_AUTHORIZE_PUBLICATION')
        status='PENDING_HUMAN_REVIEW'
        for position,event in enumerate(item['events'],1):
            if not isinstance(event,dict) or set(event)!={'action','reason_code','reviewer','at','sequence'}:raise ValueError('INVALID_REVIEW_EVENT')
            action=event['action']
            if not isinstance(action,str) or action not in REASONS or not isinstance(event['reason_code'],str) or event['reason_code'] not in REASONS[action]:raise ValueError('INVALID_REVIEW_DECISION')
            if not isinstance(event['reviewer'],str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}',event['reviewer']):raise ValueError('INVALID_REVIEWER')
            if type(event['sequence']) is not int or event['sequence']!=position:raise ValueError('INVALID_REVIEW_SEQUENCE')
            timestamp(event['at']);status='EDITORIAL_APPROVED' if action=='approve' else 'EDITORIAL_REJECTED'
        if item['status']!=status:raise ValueError('INCONSISTENT_REVIEW_STATUS')
    return reviews


def enqueue(state,video,srt,source_sha,revision,created_at):
    if not srt.is_file() or srt.is_symlink():raise ValueError('REVIEW_SRT_MISSING_OR_SYMLINK')
    key=digest(video);record={'video_sha256':key,'srt_sha256':digest(srt),'source_sha256':source_sha,
        'revision':revision,'created_at':created_at,'status':'PENDING_HUMAN_REVIEW','events':[],
        'publication_approved':False}
    reviews=state.setdefault('reviews',{})
    if key in reviews:
        if any(reviews[key][k]!=record[k] for k in ('srt_sha256','source_sha256','revision')):raise ValueError('REVIEW_HASH_BINDING_CONFLICT')
        return key
    validate_reviews({key:record},[key]);reviews[key]=record
    return key


def decide(state,key,video,srt,action,reason,reviewer,expected_events,confirmed=False):
    from .github_state import validate
    validate(state)
    if confirmed is not True:raise ValueError('EXPLICIT_HUMAN_REVIEW_ATTESTATION_REQUIRED')
    item=state.get('reviews',{}).get(key)
    if item is None:raise ValueError('UNKNOWN_REVIEW_ITEM')
    if type(expected_events) is not int or expected_events!=len(item['events']):raise ValueError('STALE_REVIEW_DECISION')
    if video.is_symlink() or srt.is_symlink() or digest(video)!=key or digest(srt)!=item['srt_sha256']:raise ValueError('REVIEW_MEDIA_HASH_MISMATCH')
    event={'action':action,'reason_code':reason,'reviewer':reviewer,'sequence':len(item['events'])+1,
        'at':datetime.now(timezone.utc).isoformat()}
    updated={**item,'events':item['events']+[event],
        'status':'EDITORIAL_APPROVED' if action=='approve' else 'EDITORIAL_REJECTED'}
    validate_reviews({key:updated},state['videos'])
    state['reviews'][key]=updated
    return updated


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation',choices=('list','decide'))
    p.add_argument('--state',type=Path,default=Path('work/cloud-state.json'))
    p.add_argument('--id');p.add_argument('--video',type=Path);p.add_argument('--srt',type=Path)
    p.add_argument('--action',choices=tuple(REASONS));p.add_argument('--reason-code');p.add_argument('--reviewer')
    p.add_argument('--expected-events',type=int);p.add_argument('--confirm-human-review',action='store_true')
    args=p.parse_args()
    from .github_state import validate
    state=validate(json.loads(args.state.read_text()))
    if args.operation=='decide':
        if any(x is None for x in (args.id,args.video,args.srt,args.action,args.reason_code,args.reviewer,args.expected_events)):p.error('Decision requires id, media files, action, reason code, reviewer and expected-events')
        decide(state,args.id,args.video,args.srt,args.action,args.reason_code,args.reviewer,args.expected_events,args.confirm_human_review)
        save(args.state,state)
    print(json.dumps({'reviews':state.get('reviews',{}),'publication_enabled':False},indent=2))


if __name__=='__main__':main()
