"""Reproducible diagnostic on a CC-BY film; never creates channel-approved output."""
import argparse
import hashlib
import importlib.metadata
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from .chopify_backend import execute, REVISION, verify_checkout, asr_model as checked_model, ASR_MODELS
from .engine import digest, probe, qa, run, save

MOVIE_URL = 'https://download.blender.org/demo/movies/ToS/tears_of_steel_720p.mov'
MOVIE_SHA = 'efa9062d9cdb7a338e40ad530dfdf234806743f29ae6a1a136b97ece4e588e8f'
LICENSE_URL = 'https://mango.blender.org/sharing/'
LICENSE = 'https://creativecommons.org/licenses/by/3.0/'
ATTRIBUTION = '(CC) Blender Foundation | mango.blender.org — Tears of Steel — CC BY 3.0. Excerpt, crop, captions and audio normalization modified. No endorsement implied.'
# Official TOS-en.srt cues 1-9, excluding the non-spoken "Fourty years later" card.
REFERENCE = "You're a jerk Thom Look Celia we have to follow our passions you have your robotics and I just want to be awesome in space Why don't you just admit that you're freaked out by my robot hand I'm not freaked out by it's alright Fine I'm freaked out I have nightmares that I'm being chased by these giant robotic claws of death Whatever Thom We're done"


def word_error(reference, hypothesis):
    def words(text): return re.findall(r'\w+', text.casefold())
    a,b = words(reference), words(hypothesis)
    if not a: raise ValueError('Reference transcript is empty')
    previous = list(range(len(b)+1))
    for i, word in enumerate(a,1):
        current=[i]
        for j, other in enumerate(b,1):
            current.append(min(previous[j]+1,current[j-1]+1,previous[j-1]+(word!=other)))
        previous=current
    return {'word_errors':previous[-1],'reference_words':len(a),'hypothesis_words':len(b),
            'wer':round(previous[-1]/len(a),4),'reference_scope':'official English subtitles; selected opening dialogue, not on-screen text'}


def obtain_movie(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if digest(path)!=MOVIE_SHA: raise ValueError('Movie SHA mismatch; existing file preserved')
        return
    temporary=path.with_suffix('.part')
    try:
        with urllib.request.urlopen(MOVIE_URL,timeout=30) as response, temporary.open('wb') as file:
            checksum=hashlib.sha256(); total=0
            while block:=response.read(1024**2):
                total+=len(block)
                if total>400_000_000: raise ValueError('Movie exceeds fixed validation limit')
                checksum.update(block);file.write(block)
        if checksum.hexdigest()!=MOVIE_SHA: raise ValueError('Downloaded movie SHA mismatch')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def validate(movie,upstream,output,model='small'):
    model=checked_model(model)
    if digest(movie)!=MOVIE_SHA: raise ValueError('Unverified validation movie')
    verify_checkout(upstream)
    output.mkdir(parents=True,exist_ok=True)
    report={'schema':1,'generated_at':datetime.now(timezone.utc).isoformat(),
            'scope':'LICENSED_REAL_MEDIA_DIAGNOSTIC_ONLY','production_eligible':False,
            'publication_enabled':False,'editorial_approved':False,
            'source':{'title':'Tears of Steel','url':MOVIE_URL,'sha256':MOVIE_SHA,
                      'license_url':LICENSE,'rights_reference':LICENSE_URL,'attribution':ATTRIBUTION,
                      'original_interval_seconds':[22,46]},'upstream_revision':REVISION}
    (output/'ATTRIBUTION.txt').write_text(ATTRIBUTION+'\nLicense: '+LICENSE+'\nSource: '+MOVIE_URL+'\nRights: '+LICENSE_URL+'\n',encoding='utf-8')
    try:
        media=output/'input';media.mkdir(exist_ok=True)
        scene=media/'opening-dialogue.mp4'
        # Always derive from the verified original; never trust an edited cached excerpt.
        run(['ffmpeg','-y','-hide_banner','-loglevel','error','-ss','22','-i',movie,'-t','24',
             '-c:v','libx264','-preset','veryfast','-crf','18','-threads','2','-c:a','aac',scene])
        source={'path':scene.name,'asr_model':model,'rights':{'verified':True,'kind':'licensed','holder':'Blender Foundation',
                'reference':LICENSE_URL,'verified_by':'Primary film sharing/download pages checked by agent',
                'verified_at':'2026-11-09'}}
        pipeline=execute(source,media,upstream,output/'pipeline')
        report['automatic_pipeline_status']=pipeline['status']
        report['automatic_output_count']=len(pipeline['outputs'])
        project=output/'pipeline/project'
        transcription=json.loads((project/'transcript.json').read_text())
        report['asr']={'model':transcription['model'],'language':transcription['language'],
                       'word_count':len(transcription['words']),
                       **word_error(REFERENCE,' '.join(w['word'] for w in transcription['words']))}
        report['asr']['review_required']=True
        report['selection']=json.loads((project/'selection.json').read_text())
        candidates=json.loads((project/'candidates.json').read_text())['candidates']
        if not candidates: raise ValueError('No diagnostic candidate; no fallback fabricated')
        candidate=candidates[0]
        report['reference_render']={'note':'Explicit renderer diagnostic of best candidate, even if editorial threshold rejects it; never enters production queue',
                                   'start':candidate['start'],'end':candidate['end'],'score':candidate['overall']}
        sys.path.insert(0,str(upstream))
        import render_clips
        import tighten
        reference=output/'reference';reference.mkdir(exist_ok=True)
        detection=render_clips.detect_track
        def observed(*args,**kwargs):
            track=detection(*args,**kwargs)
            report['tracking']={'samples':len(track),'face_detected_samples':sum(x is not None for _,x in track),
                                'active_speaker_verified':False}
            save(reference/'tracking.json',{'raw_track':[(float(t),None if c is None else float(c)) for t,c in track],
                                           **report['tracking']})
            return track
        render_clips.detect_track=observed
        segment={**candidate,'id':'diagnostic','hook':'not-approved'}
        video=render_clips.render(segment,transcription['words'],scene,1280,534,project,'9:16',out_dir=reference,
                                  style='bold',do_tighten=True,loudnorm=True,caption={'words_per_cue':3})
        # Attribution and diagnostic status travel with the MP4 as well as the sidecar.
        marked=reference/'licensed-reference-NOT-APPROVED.mp4'
        run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',video,
             '-vf',"drawtext=text='DIAGNOSTIC - NOT APPROVED':fontsize=32:fontcolor=white:box=1:boxcolor=black@0.6:x=(w-tw)/2:y=70,drawtext=text='CC BY 3.0 - Blender Foundation - mango.blender.org':fontsize=25:fontcolor=white:box=1:boxcolor=black@0.6:x=(w-tw)/2:y=h-70",
             '-metadata','title=Tears of Steel - diagnostic not approved','-metadata','comment='+ATTRIBUTION,
             '-c:v','libx264','-preset','veryfast','-threads','2','-crf','20','-c:a','copy','-movflags','+faststart',marked])
        video.unlink()
        for extension in ('.srt','.png','.meta.json'):
            old=video.with_suffix(extension)
            if old.exists(): old.rename(marked.with_suffix(extension))
        keeps=tighten.plan_cuts(transcription['words'],candidate['start'],candidate['end'])
        mapped,duration=tighten.remap_words(transcription['words'],candidate['start'],keeps)
        save(marked.with_suffix('.meta.json'),{'title':'Tears of Steel - diagnostic not approved','attribution':ATTRIBUTION,'license_url':LICENSE,'production_eligible':False,'editorial_approved':False,'publication_approved':False})
        report['reference_render'].update(video=str(marked.relative_to(output)),sha256=digest(marked),
                                         qa=qa(marked,mapped,duration),keep_ranges=keeps)
        report['dependencies']={name:importlib.metadata.version(name) for name in ('av','faster-whisper','ctranslate2','opencv-python','numpy')}
        report['status']='DIAGNOSTIC_COMPLETED_NO_EDITORIAL_APPROVAL'
        report['limitations']=['English film, not Portuguese GTA RP footage',
                              'Reference render bypasses selection solely for diagnostics, never approval',
                              'ASR transcript and speaker framing need human review']
    except Exception as error:
        report.update(status='FAILED',reason=str(error))
        raise
    finally:
        save(output/'validation.json',report)
        (output/'README.md').write_text('# Real-media diagnostic\n\nNOT APPROVED FOR THE CHANNEL.\n\n'+ATTRIBUTION+'\n\nSee validation.json for ASR, selection, tracking and QA.\n',encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--movie',type=Path,default=Path('work/real-film/tears-of-steel.mov'))
    p.add_argument('--upstream',type=Path,default=Path('work/chopify'))
    p.add_argument('--output',type=Path,default=Path('work/real-validation'))
    p.add_argument('--download',action='store_true')
    p.add_argument('--asr-model',choices=ASR_MODELS,default='small')
    args=p.parse_args()
    if args.download: obtain_movie(args.movie)
    if not args.movie.exists(): p.error('Movie missing; use --download for the fixed licensed source')
    report=validate(args.movie.resolve(),args.upstream.resolve(),args.output.resolve(),model=args.asr_model)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
