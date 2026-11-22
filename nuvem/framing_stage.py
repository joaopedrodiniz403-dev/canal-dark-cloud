"""Optional post-selection framing. Never promotes rejected or unverified candidates."""
import json
import math
import sys
from pathlib import Path
from .engine import digest, qa, save
from .framing import analyze, plan_dual, crops_at, coverage, render_dual

MODES=('native','preserve_two_faces')


def framing_mode(value='native'):
    if not isinstance(value,str) or value not in MODES:
        raise ValueError('FRAMING_MODE_UNSUPPORTED')
    return value


def selected_segment(video,source,project):
    """Bind output interval/score to the pinned backend's selected segments."""
    meta=json.loads(video.with_suffix('.meta.json').read_text())
    selected=json.loads((project/'segments.json').read_text())
    transcript=json.loads((project/'transcript.json').read_text())
    if Path(transcript.get('video','')).resolve()!=source.resolve():
        raise ValueError('FRAMING_SOURCE_MISMATCH')
    def number(value):
        return type(value) in (int,float) and math.isfinite(value)
    if not all(number(meta.get(k)) for k in ('start','end','score')):
        raise ValueError('FRAMING_INVALID_METADATA')
    if not 0<=meta['start']<meta['end'] or not 15<=meta['end']-meta['start']<=59 or meta['score']<8:
        raise ValueError('FRAMING_SELECTOR_REJECTED')
    matches=[s for s in selected if all(number(s.get(k)) for k in ('start','end','overall'))
             and abs(s['start']-meta['start'])<.001 and abs(s['end']-meta['end'])<.001
             and abs(s['overall']-meta['score'])<.001 and s['overall']>=8]
    if len(matches)!=1:
        raise ValueError('FRAMING_SELECTION_MISMATCH')
    if not isinstance(transcript.get('words'),list) or not transcript['words']:
        raise ValueError('FRAMING_TRANSCRIPT_MISSING')
    return matches[0],transcript['words'],meta


def apply_selected(video,source,project,upstream,work,rights,attribution=''):
    work.mkdir(parents=True,exist_ok=True)
    report={'native_video_sha256':digest(video),'status':'STARTED','editorial_approved':False,
            'publication_approved':False,'active_speaker_verified':False,'output':None}
    try:
        segment,words,meta=selected_segment(video,source,project)
        report['source_interval']=[segment['start'],segment['end']]
        report['selection_score']=segment['overall']
        sys.path.insert(0,str(upstream))
        import tighten
        keeps=tighten.plan_cuts(words,segment['start'],segment['end'])
        mapped,duration=tighten.remap_words(words,segment['start'],keeps)
        common=work/'source-for-framing.mp4'
        tighten.apply_cuts(source,keeps,segment['start'],common)
        samples,width,height,kind=analyze(common,work/'analysis',upstream)
        plan=plan_dual(samples,width,height)
        save(work/'plan.json',plan)
        report.update(plan_status=plan['status'],detector=kind)
        if plan['status']!='DUAL_FACE_DIAGNOSTIC':
            report['status']='REJECTED_FRAMING_UNCERTAINTY';return report
        geometric=coverage(samples,lambda t:crops_at(plan,t,width,height))
        report['source_face_geometry']=geometric
        if geometric['face_visibility_ratio'] is None or geometric['face_visibility_ratio']<.95:
            report['status']='REJECTED_FRAMING_GEOMETRY';return report
        rendered=render_dual(common,mapped,plan,width,height,duration,work/'render',upstream)
        quality=qa(rendered,mapped,duration)
        report['technical_qa']=quality
        if not quality['passed']:
            report['status']='REJECTED_FRAMING_TECHNICAL_QA';return report
        final=rendered.with_name('review.mp4')
        rendered.replace(final)
        rendered.with_suffix('.srt').replace(final.with_suffix('.srt'))
        save(final.with_suffix('.meta.json'),{**meta,'rights':rights,'attribution':attribution,
            'framing_mode':'preserve_two_faces','editorial_approved':False,'publication_approved':False})
        report.update(status='APPLIED_PENDING_HUMAN_REVIEW',output=str(final),output_sha256=digest(final))
        return report
    except ValueError as error:
        report.update(status='REJECTED_FRAMING_INPUT',reason=str(error));return report
    except Exception as error:
        report.update(status='FAILED',reason=str(error));return report
    finally:
        save(work/'framing.json',report)


def process_outputs(source_record,source,output,upstream,outputs):
    """Return only staged review outputs; native exports remain untouched, unqueued."""
    accepted=[];reports=[]
    for relative in outputs:
        video=(output/relative).resolve()
        exports=(output/'exports').resolve()
        if not video.is_relative_to(exports) or not video.is_file():
            raise ValueError('FRAMING_OUTPUT_PATH_REJECTED')
        work=output/'framing'/digest(video)[:20]
        report=apply_selected(video,source,output/'project',upstream,work,source_record['rights'],source_record.get('attribution',''))
        reports.append(report)
        if report['status']=='APPLIED_PENDING_HUMAN_REVIEW':
            final=Path(report['output']).resolve()
            if not final.is_relative_to(work.resolve()) or not final.is_file():
                raise ValueError('FRAMING_REVIEW_PATH_REJECTED')
            accepted.append(str(final.relative_to(output)))
    result={'mode':'preserve_two_faces','status':'REVIEW_REQUIRED' if accepted else 'FRAMING_REJECTED',
            'items':reports,'editorial_approved':False,'publication_approved':False}
    save(output/'framing_report.json',result)
    if any(item['status']=='FAILED' for item in reports):
        raise RuntimeError('FRAMING_PROCESSING_FAILED; inspect framing_report.json')
    return accepted,result
