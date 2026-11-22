"""Re-render pinned native portrait tracking with one bounded readable ASS/SRT plan."""
import contextlib
import hashlib
import json
import shutil
import sys
import threading
from pathlib import Path
from .caption_reflow import write
from .engine import digest,probe,qa,save
from .framing_stage import selected_segment

_LOCK=threading.Lock()


def signature(words,start,end):
    return hashlib.sha256(json.dumps([words,start,end],sort_keys=True,ensure_ascii=False).encode()).hexdigest()


@contextlib.contextmanager
def caption_hooks(renderer,captions,output):
    """Process-local adapters; restore upstream functions even on render failure."""
    with _LOCK:
        original_ass,original_srt=renderer.build_ass,captions.write_srt
        record={};shared=output/'captions.srt'
        def build_ass(words,start,end,path,width,height,*args,**kwargs):
            if start!=0 or (width,height)!=(1080,1920):raise ValueError('READABLE_RETIMED_PORTRAIT_REQUIRED')
            quality=write(words,end,Path(path),shared,center=False)
            shutil.copyfile(path,output/'captions.ass')
            shutil.copyfile(Path(path).with_suffix('.plan.json'),output/'captions.plan.json')
            record.update(timeline_sha256=signature(words,start,end),ass_sha256=digest(Path(path)),
                          srt_sha256=digest(shared),caption_audit=quality,editorial_approved=False)
            save(output/'caption-render.json',record)
        def write_srt(words,start,end,path,group_size=8):
            if signature(words,start,end)!=record.get('timeline_sha256'):raise ValueError('READABLE_EXPORT_TIMELINE_MISMATCH')
            Path(path).write_bytes(shared.read_bytes());return Path(path)
        renderer.build_ass,captions.write_srt=build_ass,write_srt
        try:yield record
        finally:renderer.build_ass,captions.write_srt=original_ass,original_srt


def render(segment,words,source,width,height,project,output,upstream):
    from .chopify_backend import verify_checkout
    verify_checkout(upstream);sys.path.insert(0,str(upstream))
    import render_clips,captions,tighten
    from .continuous_tighten import hook
    output.mkdir(parents=True,exist_ok=True)
    with caption_hooks(render_clips,captions,output),hook(tighten):
        return render_clips.render(segment,words,source,width,height,project,'9:16',out_dir=output,
            style='bold',do_tighten=True,loudnorm=True,caption={'words_per_cue':3})


def process_outputs(source_record,source,output,upstream,outputs):
    accepted=[];items=[]
    report={'status':'CAPTIONS_REJECTED','items':items,'editorial_approved':False,'publication_approved':False}
    try:
        for relative in outputs:
            native=(output/relative).resolve()
            if not native.is_relative_to((output/'exports').resolve()) or not native.is_file():raise ValueError('READABLE_OUTPUT_PATH_REJECTED')
            item={'native_video_sha256':digest(native),'status':'REJECTED'};items.append(item)
            try:
                segment,words,_=selected_segment(native,source,output/'project')
                data=probe(source);stream=next(s for s in data['streams'] if s['codec_type']=='video')
                target=output/'readable'/digest(native)[:20]
                video=render(segment,words,source,stream['width'],stream['height'],output/'project',target,upstream)
                import tighten
                keeps=tighten.plan_cuts(words,segment['start'],segment['end'])
                mapped,duration=tighten.remap_words(words,segment['start'],keeps)
                quality=qa(video,mapped,duration);item['technical_qa']=quality
                if not quality['passed']:
                    item['status']='REJECTED_TECHNICAL_QA';continue
                meta=json.loads(video.with_suffix('.meta.json').read_text())
                save(video.with_suffix('.meta.json'),{**meta,'rights':source_record['rights'],
                     'attribution':source_record.get('attribution',''),'caption_mode':'readable',
                     'editorial_approved':False,'publication_approved':False})
                relative=str(video.relative_to(output));accepted.append(relative)
                item.update(status='PENDING_HUMAN_REVIEW',output=relative,video_sha256=digest(video))
            except ValueError as error:item.update(status='REJECTED_INPUT_OR_PLAN',reason=str(error))
        report['status']='PENDING_HUMAN_REVIEW' if accepted else 'CAPTIONS_REJECTED'
        return accepted,report
    except Exception:
        report['status']='FAILED';raise
    finally:save(output/'readable_report.json',report)
