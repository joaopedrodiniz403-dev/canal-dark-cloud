"""Render existing keep ranges with one AAC encode, avoiding per-part priming."""
import contextlib
import math
import json
import os
import subprocess
import tempfile
from pathlib import Path


def graph_for(keeps,clip_start,source_offset=0):
    if not keeps or len(keeps)>256:raise ValueError('INVALID_KEEP_COUNT')
    if not all(type(x) in (int,float) and math.isfinite(x) and x>=0 for x in (clip_start,source_offset)):
        raise ValueError('INVALID_SOURCE_OFFSET')
    previous=0;filters=[];labels=[];total=0
    for index,pair in enumerate(keeps):
        if len(pair)!=2:raise ValueError('INVALID_KEEP_RANGE')
        a,b=pair
        if not all(type(x) in (int,float) and math.isfinite(x) for x in (a,b)) or not 0<=previous<=a<b:
            raise ValueError('INVALID_KEEP_RANGE')
        start=clip_start+a-source_offset;end=clip_start+b-source_offset
        if start<0:raise ValueError('KEEP_BEFORE_LOCAL_SOURCE')
        total+=b-a;previous=b
        filters.extend([f'[0:v:0]trim=start={start:.6f}:end={end:.6f},setpts=PTS-STARTPTS[v{index}]',
                        f'[0:a:0]atrim=start={start:.6f}:end={end:.6f},asetpts=PTS-STARTPTS[a{index}]'])
        labels.append(f'[v{index}][a{index}]')
    if total>60:raise ValueError('TIGHTEN_DURATION_LIMIT')
    filters.append(''.join(labels)+f'concat=n={len(keeps)}:v=1:a=1[vc][a]'
                   ';[vc]fps=30[v]')
    return ';\n'.join(filters)


def apply_cuts(source,keeps,clip_start,out_path,crf=18,source_offset=0):
    graph=graph_for(keeps,clip_start,source_offset)
    if type(crf) is not int or not 0<=crf<=51:raise ValueError('INVALID_CRF')
    target=Path(out_path);target.parent.mkdir(parents=True,exist_ok=True)
    # Only promote a completed output. Input/source paths never enter the graph.
    with tempfile.TemporaryDirectory(prefix='.continuous-',dir=target.parent) as tmp:
        tmp=Path(tmp);script=tmp/'filters.txt';script.write_text(graph,encoding='utf-8')
        video=tmp/'tightened.mp4'
        result=subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','warning','-i',str(source),
            '-filter_complex_threads','2','-filter_complex_script',str(script),'-map','[v]','-map','[a]',
            '-c:v','libx264','-preset','veryfast','-crf',str(crf),'-threads','2',
            '-c:a','aac','-b:a','160k',str(video)],check=True,capture_output=True,timeout=300)
        os.replace(video,target)
        warnings=result.stderr.decode('utf-8',errors='replace').lower()
        target.with_suffix('.continuous.json').write_text(json.dumps({
            'scope':'SINGLE_AAC_ENCODE_TECHNICAL_REPORT','keep_count':len(keeps),
            'duration_seconds':sum(b-a for a,b in keeps),'video_fps':30,
            'non_monotonic_warning_count':warnings.count('non-monoton'),
            'backward_audio_warning_count':warnings.count('backward in time'),
            'editorial_approved':False},indent=2)+'\n',encoding='utf-8')
    return target


@contextlib.contextmanager
def hook(tighten):
    """Caller serializes native rendering; always restore the pinned upstream."""
    original=tighten.apply_cuts
    tighten.apply_cuts=apply_cuts
    try:yield
    finally:tighten.apply_cuts=original
