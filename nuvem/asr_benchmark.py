"""Compare allowed ASR models on the same verified CC-BY scene; never approves media."""
import argparse
import json
import math
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from .chopify_backend import ASR_MODELS, asr_model, verify_checkout, REVISION
from .engine import digest, run, save
from .real_validation import MOVIE_SHA, MOVIE_URL, ATTRIBUTION, LICENSE, REFERENCE, obtain_movie, word_error


def summarize(rows):
    if len(rows)!=2 or {r['model'] for r in rows}!={'small','medium'}:
        raise ValueError('Comparison requires one small and one medium result')
    for row in rows:
        for key in ('wer','transcribe_seconds','load_seconds'):
            value=row.get(key)
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
                raise ValueError('Invalid benchmark measurement')
        if row['transcribe_seconds']==0:
            raise ValueError('Inference duration must be positive')
    by_model={r['model']:r for r in rows}
    if any(r['source_sha256']!=by_model['small']['source_sha256'] for r in rows):
        raise ValueError('Cannot compare different source bytes')
    if any(r['device']!='cpu' or r['compute_type']!='int8' or r['cpu_threads']!=4 or
           r['reference_sha256']!=by_model['small']['reference_sha256'] for r in rows):
        raise ValueError('Cannot compare different decode settings or references')
    small,medium=by_model['small'],by_model['medium']
    delta=small['wer']-medium['wer']
    return {'wer_small':small['wer'],'wer_medium':medium['wer'],
            'wer_reduction_percentage_points':round(100*delta,3),
            'lower_wer_model':'medium' if delta>0 else 'small' if delta<0 else 'tie',
            'inference_ratio_medium_over_small':round(medium['transcribe_seconds']/small['transcribe_seconds'],3) if small['transcribe_seconds'] else None,
            'production_default_changed':False,'editorial_approval':False,
            'scope':'One English film scene, not a Portuguese/GTA RP benchmark'}


def transcribe_one(source,upstream,model):
    model=asr_model(model)
    verify_checkout(upstream)
    sys.path.insert(0,str(upstream))
    from faster_whisper import WhisperModel
    from download_and_transcribe import _transcribe_media
    start=time.monotonic()
    engine=WhisperModel(model,device='cpu',compute_type='int8',cpu_threads=4)
    load=time.monotonic()-start;start=time.monotonic()
    segments,words,language,duration=_transcribe_media(engine,source)
    elapsed=time.monotonic()-start
    import hashlib
    return {'model':model,'source_sha256':digest(source),
            'reference_sha256':hashlib.sha256(REFERENCE.encode()).hexdigest(),
            'device':'cpu','compute_type':'int8','cpu_threads':4,'language':language,
            'load_seconds':round(load,3),'transcribe_seconds':round(elapsed,3),
            'load_time_includes_download_if_needed':True,'word_count':len(words),
            'transcript':' '.join(w['word'] for w in words),'words':words,
            **word_error(REFERENCE,' '.join(w['word'] for w in words))}


def benchmark(movie,upstream,output):
    if digest(movie)!=MOVIE_SHA:raise ValueError('Unverified validation movie')
    verify_checkout(upstream)
    output.mkdir(parents=True,exist_ok=True)
    report={'status':'STARTED','generated_at':datetime.now(timezone.utc).isoformat(),
            'source_movie_url':MOVIE_URL,'source_movie_sha256':MOVIE_SHA,
            'interval':[22,46],'license_url':LICENSE,'attribution':ATTRIBUTION,
            'upstream_revision':REVISION,'production_eligible':False,'publication_enabled':False,'results':[]}
    (output/'ATTRIBUTION.txt').write_text(ATTRIBUTION+'\n'+LICENSE+'\n',encoding='utf-8')
    scene=output/'scene.mp4'
    try:
        run(['ffmpeg','-y','-hide_banner','-loglevel','error','-ss','22','-i',movie,'-t','24',
             '-c:v','libx264','-preset','veryfast','-crf','18','-threads','2','-c:a','aac',scene])
        for model in ASR_MODELS:
            result=output/(model+'.json')
            # Separate processes bound peak memory and avoid retaining both models in RAM.
            args=[sys.executable,'-m','nuvem.asr_benchmark','--worker',model,'--source',str(scene),
                  '--upstream',str(upstream),'--output',str(result)]
            with (output/(model+'.log')).open('w') as log:
                subprocess.run(args,check=True,timeout=900,stdout=log,stderr=subprocess.STDOUT)
            report['results'].append(json.loads(result.read_text()))
            save(output/'comparison.json',report)
        report['comparison']=summarize(report['results'])
        report['status']='COMPARED_NO_EDITORIAL_APPROVAL'
    except Exception as error:
        report.update(status='FAILED',reason=str(error));raise
    finally:
        save(output/'comparison.json',report)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--movie',type=Path,default=Path('work/real-film/tears-of-steel.mov'))
    p.add_argument('--upstream',type=Path,default=Path('work/chopify'))
    p.add_argument('--output',type=Path,default=Path('work/asr-comparison'))
    p.add_argument('--download',action='store_true')
    p.add_argument('--worker',choices=ASR_MODELS,help=argparse.SUPPRESS)
    p.add_argument('--source',type=Path,help=argparse.SUPPRESS)
    args=p.parse_args()
    if args.worker:
        if args.source is None:p.error('Worker source missing')
        save(args.output,transcribe_one(args.source.resolve(),args.upstream.resolve(),args.worker));return
    if args.download:obtain_movie(args.movie)
    report=benchmark(args.movie.resolve(),args.upstream.resolve(),args.output.resolve())
    print(json.dumps(report['comparison'],indent=2))


if __name__=='__main__':main()
