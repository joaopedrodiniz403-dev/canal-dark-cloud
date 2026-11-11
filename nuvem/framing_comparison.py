"""Compare existing largest-face crop with a two-face diagnostic on licensed media."""
import argparse
import bisect
import json
import shutil
import sys
from datetime import datetime,timezone
from pathlib import Path
from .chopify_backend import verify_checkout
from .engine import digest, probe, qa, run, save
from .framing import analyze, plan_dual, crops_at, coverage, render_dual
from .real_validation import MOVIE_SHA, ATTRIBUTION, LICENSE


def mark(video,output,label):
    run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',video,
         '-vf',f"drawtext=text='{label} - NOT APPROVED':fontsize=30:fontcolor=white:box=1:boxcolor=black@0.6:x=(w-tw)/2:y=60,drawtext=text='CC BY 3.0 - Blender Foundation - mango.blender.org':fontsize=25:fontcolor=white:box=1:boxcolor=black@0.6:x=(w-tw)/2:y=h-60",
         '-metadata','comment='+ATTRIBUTION,'-c:v','libx264','-preset','veryfast','-crf','20','-threads','2','-c:a','copy','-movflags','+faststart',output])


def compare(validation,upstream,output):
    verify_checkout(upstream)
    prior=json.loads((validation/'validation.json').read_text())
    if prior.get('source',{}).get('sha256')!=MOVIE_SHA:
        raise ValueError('Only the reviewed CC BY validation source is supported')
    output.mkdir(parents=True,exist_ok=True)
    (output/'ATTRIBUTION.txt').write_text(ATTRIBUTION+'\n'+LICENSE+'\n')
    report={'generated_at':datetime.now(timezone.utc).isoformat(),'scope':'FRAMING_DIAGNOSTIC_ONLY',
            'production_eligible':False,'editorial_approved':False,'publication_enabled':False,
            'attribution':ATTRIBUTION,'active_speaker_verified':False,'production_default_changed':False}
    try:
        sys.path.insert(0,str(upstream))
        import render_clips
        import tighten
        source=validation/'input/opening-dialogue.mp4'
        transcript=json.loads((validation/'pipeline/project/transcript.json').read_text())
        segment=prior['reference_render']
        keeps=tighten.plan_cuts(transcript['words'],segment['start'],segment['end'])
        words,duration=tighten.remap_words(transcript['words'],segment['start'],keeps)
        common=output/'common-input.mp4'
        tighten.apply_cuts(source,keeps,segment['start'],common)
        work=output/'analysis';work.mkdir(exist_ok=True)
        # Reuse the detector downloaded by the reviewed pinned backend, if available.
        detector=validation/'pipeline/yunet.onnx'
        if detector.exists():shutil.copyfile(detector,output/'yunet.onnx')
        samples,width,height,kind=analyze(common,work,upstream)
        plan=plan_dual(samples,width,height)
        save(work/'dual-plan.json',plan)
        report.update(source_sha256=digest(common),duration=duration,detector=kind,
                      detection_samples=len(samples),plan_status=plan['status'])
        if plan['status']!='DUAL_FACE_DIAGNOSTIC':
            report['status']='NO_SAFE_DUAL_PLAN';return report
        raw=render_clips.detect_track(common,0,duration,width,work)
        cw,ch,x0,y0=render_clips.crop_for(width,height,1080,1920)
        smooth=render_clips.smooth_track(raw,width,cw)
        commands=[];last=None
        for t,cx in smooth:
            x=int(round(cx-cw/2))
            if last is None or abs(x-last)>=2:commands.append((t,x));last=x
        times=[x[0] for x in commands]
        def baseline_crops(t):
            index=max(0,bisect.bisect_right(times,t)-1)
            return [[commands[index][1],y0,cw,ch]]
        report['baseline_coverage']=coverage(samples,baseline_crops)
        report['plan_summary']={'ranges':plan['ranges'],'panel_size':plan['panel_size']}
        report['dual_coverage']=coverage(samples,lambda t:crops_at(plan,t,width,height))
        base=output/'baseline';base.mkdir(exist_ok=True)
        original=render_clips.detect_track
        render_clips.detect_track=lambda *args,**kwargs:raw
        try:
            native=render_clips.render({'start':0,'end':duration,'hook':'baseline-not-approved'},words,common,
                                      width,height,work,'9:16',out_dir=base,style='bold',loudnorm=True,
                                      caption={'words_per_cue':3})
        finally:render_clips.detect_track=original
        baseline=base/'largest-face-NOT-APPROVED.mp4'
        mark(native,baseline,'LARGEST FACE');native.unlink()
        if native.with_suffix('.srt').exists():native.with_suffix('.srt').rename(baseline.with_suffix('.srt'))
        for suffix in ('.png','.meta.json'):native.with_suffix(suffix).unlink(missing_ok=True)
        dual_dir=output/'dual';dual=render_dual(common,words,plan,width,height,duration,dual_dir,upstream)
        marked=dual_dir/'two-faces-NOT-APPROVED.mp4'
        mark(dual,marked,'TWO FACES');dual.unlink()
        if dual.with_suffix('.srt').exists():dual.with_suffix('.srt').rename(marked.with_suffix('.srt'))
        report['outputs']=[]
        for name,video,metrics in [('baseline',baseline,report['baseline_coverage']),('dual',marked,report['dual_coverage'])]:
            save(video.with_suffix('.meta.json'),{'attribution':ATTRIBUTION,'license':LICENSE,'production_eligible':False,'editorial_approved':False,'publication_approved':False})
            report['outputs'].append({'layout':name,'video':str(video.relative_to(output)),'sha256':digest(video),
                                      'technical_qa':qa(video,words,duration),
                                      'observed_face_geometry_gate':metrics['face_visibility_ratio'] is not None and metrics['face_visibility_ratio']>=.95,
                                      'editorial_approved':False})
        report['status']='COMPARED_NO_EDITORIAL_APPROVAL'
        report['limitations']=['Detected face boxes are not ground truth or active-speaker identity',
                              'Left/right association is spatial and may swap people who cross',
                              'Only one English film scene; no Portuguese/GTA RP validation',
                              'This experimental layout is not wired into production']
    except Exception as error:
        report.update(status='FAILED',reason=str(error));raise
    finally:
        save(output/'framing.json',report)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--validation',type=Path,default=Path('work/real-validation'))
    p.add_argument('--upstream',type=Path,default=Path('work/chopify'))
    p.add_argument('--output',type=Path,default=Path('work/framing-comparison'))
    args=p.parse_args()
    report=compare(args.validation.resolve(),args.upstream.resolve(),args.output.resolve())
    print(json.dumps(report,indent=2))
    if report['status']!='COMPARED_NO_EDITORIAL_APPROVAL':raise SystemExit(1)


if __name__=='__main__':main()
