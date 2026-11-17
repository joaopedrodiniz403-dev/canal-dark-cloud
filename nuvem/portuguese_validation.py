"""Real Portuguese CC BY-SA interview diagnostic, never channel-approved content."""
import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import datetime,timezone
from pathlib import Path
from .engine import digest,probe,qa,run,save
from .chopify_backend import execute,REVISION,verify_checkout
from .caption_audit import audit
from .caption_reflow import plan as reflow_plan

FILE_URL='https://upload.wikimedia.org/wikipedia/commons/1/13/Entrevista_com_Murilo_S%C3%A1_Toledo.webm'
PAGE='https://commons.wikimedia.org/w/index.php?title=File:Entrevista_com_Murilo_S%C3%A1_Toledo.webm&oldid=1121577018'
SHA256='96e790b029224ffafd2d4e7d740435104a04b580109d97ee9bcf3d5af1e88021'
SHA1='887d08c0090a689735a1be49e9e425a152753c06'
LICENSE='https://creativecommons.org/licenses/by-sa/4.0/'
ATTRIBUTION='Entrevista com Murilo Sá Toledo — gravação/pós-produção: Rodrigo Tetsuo Argenton; reportagem: Érica Azzellini. Fonte: '+PAGE+' . CC BY-SA 4.0: '+LICENSE+' . Modificações: trecho, recorte vertical, normalização e legendas ASR não revisadas. Derivado distribuído em CC BY-SA 4.0; sem endosso.'
INTERVAL=(30,75)


def verify_source(path):
    if digest(path)!=SHA256 or hashlib.sha1(path.read_bytes()).hexdigest()!=SHA1:
        raise ValueError('PORTUGUESE_SOURCE_HASH_MISMATCH')


def obtain(path):
    if path.exists():verify_source(path);return
    path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_suffix('.partial')
    try:
        request=urllib.request.Request(FILE_URL,headers={'User-Agent':'NuvemEscura-research/1.0 (licensed-media-diagnostic)'})
        with urllib.request.urlopen(request,timeout=60) as response,temporary.open('wb') as target:
            total=0
            while block:=response.read(1024*1024):
                total+=len(block)
                if total>60*1024*1024:raise ValueError('PORTUGUESE_SOURCE_SIZE_LIMIT')
                target.write(block)
        verify_source(temporary);temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def licensed_source(scene):
    return {'path':scene.name,'asr_model':'small','attribution':ATTRIBUTION,
            'rights':{'verified':True,'kind':'licensed','holder':'Rodrigo Tetsuo Argenton; Érica Azzellini',
                      'reference':PAGE,'verified_at':'2026-11-17',
                      'verified_by':'Agent checked file revision 1121577018, own-work declaration, CC BY-SA 4.0 and published SHA-1'}}


def validate(movie,upstream,output):
    verify_source(movie);verify_checkout(upstream);output.mkdir(parents=True,exist_ok=True)
    report={'schema':1,'generated_at':datetime.now(timezone.utc).isoformat(),
            'scope':'LICENSED_PORTUGUESE_INTERVIEW_DIAGNOSTIC_ONLY','production_eligible':False,
            'editorial_approved':False,'publication_approved':False,'publication_enabled':False,
            'source':{'title':'Entrevista com Murilo Sá Toledo','url':FILE_URL,'rights_reference':PAGE,
                      'sha256':SHA256,'sha1':SHA1,'license_url':LICENSE,'attribution':ATTRIBUTION,
                      'original_interval_seconds':list(INTERVAL)},'upstream_revision':REVISION,
            'active_speaker_verified':False,'reference_transcript_available':False,'wer':None}
    (output/'ATTRIBUTION.txt').write_text(ATTRIBUTION+'\n',encoding='utf-8')
    try:
        media=output/'input';media.mkdir(exist_ok=True);scene=media/'interview-30-75.mp4'
        run(['ffmpeg','-y','-hide_banner','-loglevel','error','-ss',str(INTERVAL[0]),'-i',movie,'-t',str(INTERVAL[1]-INTERVAL[0]),
             '-c:v','libx264','-preset','veryfast','-crf','18','-threads','2','-c:a','aac',scene])
        result=execute(licensed_source(scene),media,upstream,output/'pipeline')
        report.update(automatic_pipeline_status=result['status'],automatic_output_count=len(result['outputs']))
        project=output/'pipeline/project';transcript=json.loads((project/'transcript.json').read_text())
        report['asr']={'model':transcript['model'],'language':transcript['language'],'word_count':len(transcript['words']),
                       'accuracy_verified':False,'human_listening_review_required':True}
        if transcript['language']!='pt':raise ValueError('PORTUGUESE_LANGUAGE_NOT_DETECTED')
        report['selection']=json.loads((project/'selection.json').read_text())
        candidates=json.loads((project/'candidates.json').read_text())['candidates']
        if not candidates:
            report['status']='NO_DIAGNOSTIC_CANDIDATE';return report
        segment={**candidates[0],'id':'pt-diagnostic','hook':'pt-not-approved'}
        report['reference_render']={'start':segment['start'],'end':segment['end'],'score':segment['overall'],
             'scope':'Renderer diagnostic of actual candidate; may be rejected by selector; never enters channel state'}
        sys.path.insert(0,str(upstream));import render_clips,tighten
        data=probe(scene);stream=next(s for s in data['streams'] if s['codec_type']=='video')
        reference=output/'reference';reference.mkdir(exist_ok=True);original=render_clips.detect_track
        def observed(*args,**kwargs):
            track=original(*args,**kwargs)
            report['tracking']={'samples':len(track),'face_detected_samples':sum(c is not None for _,c in track),
                                'active_speaker_verified':False,'subject_crop_verified':False}
            save(reference/'tracking.json',{'track':[(float(t),None if c is None else float(c)) for t,c in track],**report['tracking']})
            return track
        render_clips.detect_track=observed
        try:
            video=render_clips.render(segment,transcript['words'],scene,stream['width'],stream['height'],project,'9:16',
                out_dir=reference,style='bold',do_tighten=True,loudnorm=True,caption={'words_per_cue':3})
        finally:render_clips.detect_track=original
        marked=reference/'pt-interview-NOT-APPROVED.mp4'
        filters="drawtext=text='DIAGNOSTIC - NOT APPROVED':fontsize=30:fontcolor=white:box=1:boxcolor=black@0.6:x=(w-tw)/2:y=70,drawtext=text='CC BY-SA 4.0 - Rodrigo Tetsuo Argenton':fontsize=24:fontcolor=white:box=1:boxcolor=black@0.6:x=(w-tw)/2:y=h-105,drawtext=text='Reportagem - Erica Azzellini - Wikimedia Commons':fontsize=22:fontcolor=white:box=1:boxcolor=black@0.6:x=(w-tw)/2:y=h-65"
        run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',video,'-vf',filters,'-metadata','comment='+ATTRIBUTION,
             '-metadata','copyright=CC BY-SA 4.0','-c:v','libx264','-preset','veryfast','-crf','20','-threads','2',
             '-c:a','copy','-movflags','+faststart',marked]);video.unlink()
        for suffix in ('.srt','.png'):
            old=video.with_suffix(suffix)
            if old.exists():old.rename(marked.with_suffix(suffix))
        video.with_suffix('.meta.json').unlink(missing_ok=True)
        save(marked.with_suffix('.meta.json'),{'attribution':ATTRIBUTION,'license_url':LICENSE,'production_eligible':False,
                                             'editorial_approved':False,'publication_approved':False})
        keeps=tighten.plan_cuts(transcript['words'],segment['start'],segment['end'])
        mapped,duration=tighten.remap_words(transcript['words'],segment['start'],keeps)
        readability=reflow_plan(mapped,duration)
        save(reference/'caption-reflow-plan.json',readability)
        report['caption_reflow_feasibility']={'status':readability['status'],'cue_count':len(readability['cues']),
             'scope':'Planning only; no alternative render or approval'}
        report['reference_render'].update(video=str(marked.relative_to(output)),sha256=digest(marked),
            qa=qa(marked,mapped,duration),caption_audit=audit(marked.with_suffix('.srt').read_text(encoding='utf-8-sig'),float(probe(marked)['format']['duration']),mapped))
        report['status']='DIAGNOSTIC_COMPLETED_NO_EDITORIAL_APPROVAL'
        report['limitations']=['Portuguese interview, not GTA RP/gameplay','No independent reference transcript or measured WER',
            'ASR/captions/crop need human listening and visual review','Native selector score is heuristic, not validated editorial quality']
    except Exception as error:
        report.update(status='FAILED',reason=str(error));raise
    finally:
        save(output/'validation.json',report)
        (output/'README.md').write_text('# Portuguese real-media diagnostic\n\nNOT APPROVED FOR THE CHANNEL.\n\n'+ATTRIBUTION+'\n\nSee validation.json. No editorial or publication approval.\n',encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--movie',type=Path,default=Path('work/portuguese-source/interview.webm'))
    p.add_argument('--upstream',type=Path,default=Path('work/chopify'))
    p.add_argument('--output',type=Path,default=Path('work/portuguese-validation'))
    p.add_argument('--download',action='store_true');args=p.parse_args()
    if args.download:obtain(args.movie)
    print(json.dumps(validate(args.movie.resolve(),args.upstream.resolve(),args.output.resolve()),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
