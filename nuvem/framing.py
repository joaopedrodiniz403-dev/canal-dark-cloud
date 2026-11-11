"""Conservative two-face framing diagnostics, without active-speaker identification."""
import bisect
import math
import re
import statistics
from pathlib import Path
from .engine import probe, run, save


def visible_fraction(face, crop):
    x,y,w,h=face;cx,cy,cw,ch=crop
    area=max(0,min(x+w,cx+cw)-max(x,cx))*max(0,min(y+h,cy+ch)-max(y,cy))
    return area/(w*h) if w>0 and h>0 else 0.0


def even(value):return max(2,int(value)//2*2)


def panel_crop(face,width,height,crop_width,crop_height):
    x,y,w,h=face
    left=min(max(0,x+w/2-crop_width/2),width-crop_width)
    top=min(max(0,y+h/2-.30*crop_height),height-crop_height)
    return [int(round(left)),int(round(top)),crop_width,crop_height]


def plan_dual(samples,width,height):
    pairs=[]
    for sample in samples:
        boxes=sample['faces']
        if len(boxes)==2:
            left,right=sorted(boxes,key=lambda b:b[0]+b[2]/2)
            if right[0]+right[2]/2-(left[0]+left[2]/2) >= width*.12:
                pairs.append({'t':sample['t'],'faces':[left,right]})
    if len(pairs)<6 or len(pairs)<.2*max(1,len(samples)):
        return {'status':'INSUFFICIENT_TWO_FACE_EVIDENCE','tracks':[],'ranges':[]}
    separation=min((p['faces'][1][0]+p['faces'][1][2]/2)-(p['faces'][0][0]+p['faces'][0][2]/2) for p in pairs)
    face_width=max(b[2] for p in pairs for b in p['faces'])
    face_height=statistics.median(b[3] for p in pairs for b in p['faces'])
    cw=even(min(width,height*1.125,face_height*6*1.125,2*(separation-face_width/2-width*.02)))
    ch=even(cw/1.125)
    if ch<face_height*2.5:
        return {'status':'FACES_TOO_CLOSE_FOR_STABLE_PANELS','tracks':[],'ranges':[]}
    tracks=[{'t':p['t'],'crops':[panel_crop(b,width,height,cw,ch) for b in p['faces']]} for p in pairs]
    # Small detection gaps may be interpolated; longer unknown stretches keep the full picture.
    ranges=[];start=previous=tracks[0]['t']
    for row in tracks[1:]:
        if row['t']-previous>.75:
            ranges.append([start,previous+.25]);start=row['t']
        previous=row['t']
    ranges.append([start,previous+.25])
    return {'status':'DUAL_FACE_DIAGNOSTIC','tracks':tracks,'ranges':ranges,'panel_size':[cw,ch],
            'active_speaker_verified':False,'person_identity_verified':False}


def crops_at(plan,t,width,height):
    if plan['status']!='DUAL_FACE_DIAGNOSTIC' or not any(a<=t<b for a,b in plan['ranges']):
        return [[0,0,width,height]]
    tracks=plan['tracks'];times=[x['t'] for x in tracks];index=bisect.bisect_right(times,t)
    if index==0:return tracks[0]['crops']
    if index>=len(tracks):return tracks[-1]['crops']
    left,right=tracks[index-1],tracks[index]
    if right['t']-left['t']>.75:return [[0,0,width,height]]
    alpha=(t-left['t'])/(right['t']-left['t'])
    return [[round(a+(b-a)*alpha) for a,b in zip(ca,cb)] for ca,cb in zip(left['crops'],right['crops'])]


def coverage(samples,get_crops):
    total=visible=both_total=both_visible=0
    for sample in samples:
        crops=get_crops(sample['t']);faces=sample['faces']
        passed=[any(visible_fraction(face,crop)>=.95 for crop in crops) for face in faces]
        total+=len(faces);visible+=sum(passed)
        if len(faces)==2:
            both_total+=1;both_visible+=all(passed)
    return {'detected_faces':total,'faces_95_percent_visible':visible,
            'face_visibility_ratio':round(visible/total,4) if total else None,
            'two_face_samples':both_total,'both_faces_visible_samples':both_visible,
            'both_faces_visibility_ratio':round(both_visible/both_total,4) if both_total else None,
            'scope':'Geometry of faces detected in source, not active speaker or ground truth',
            'samples_without_detection':sum(not s['faces'] for s in samples)}


def analyze(source,work,upstream):
    import sys
    import cv2
    sys.path.insert(0,str(upstream))
    import render_clips
    data=probe(source);stream=next(s for s in data['streams'] if s['codec_type']=='video')
    width,height=stream['width'],stream['height'];work.mkdir(parents=True,exist_ok=True)
    reduced=work/'analysis.mp4'
    run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',source,'-vf','fps=4,scale=960:-2',
         '-an','-c:v','libx264','-preset','ultrafast','-threads','2',reduced])
    kind,detector=render_clips._make_detector(work)
    cap=cv2.VideoCapture(str(reduced));dw,dh=int(cap.get(3)),int(cap.get(4))
    if kind=='yunet':detector.setInputSize((dw,dh))
    samples=[];index=0
    while True:
        ok,frame=cap.read()
        if not ok:break
        if kind=='yunet':
            _,found=detector.detect(frame)
            boxes=[] if found is None else [f[:4] for f in found if f[14]>=.6]
        else:
            boxes=detector.detectMultiScale(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY),1.1,5,minSize=(24,24))
        faces=[]
        for x,y,w,h in boxes:
            face=[float(x)*width/dw,float(y)*height/dh,float(w)*width/dw,float(h)*height/dh]
            if face[2]>=width*.015 and face[3]>0:faces.append(face)
        samples.append({'t':index/4,'faces':faces});index+=1
    cap.release();reduced.unlink(missing_ok=True)
    save(work/'detections.json',{'detector':kind,'sample_fps':4,'width':width,'height':height,'samples':samples})
    return samples,width,height,kind


def validate_crop_replies(log, expected):
    replies=re.findall(r'Command reply for command #[0-9]+: ret:(.*?) res:',log)
    if not replies or len(replies)<expected*.95 or any(x.strip()!='Success' for x in replies):
        raise RuntimeError('FFMPEG_CROP_COMMAND_FAILED')
    return {'expected_commands':expected,'successful_replies':len(replies),'all_successful':True}


def render_dual(source,words,plan,width,height,duration,output,upstream):
    if plan['status']!='DUAL_FACE_DIAGNOSTIC':raise ValueError('No stable dual-face plan')
    import sys
    sys.path.insert(0,str(upstream))
    import render_clips
    from captions import write_srt
    output.mkdir(parents=True,exist_ok=True)
    # Interpolate crop motion at video rate, instead of jumping at detector sample rate.
    commands=[]
    for frame in range(math.ceil(duration*24)):
        t=frame/24
        crops=crops_at(plan,t,width,height)
        if len(crops)!=2:
            crops=plan['tracks'][0]['crops']
        for i,crop in enumerate(crops):
            commands += [f'{t:.5f} crop@p{i} x {crop[0]};',f'{t:.5f} crop@p{i} y {crop[1]};']
    (output/'crops.cmd').write_text('\n'.join(commands)+'\n')
    render_clips.build_ass(words,0,duration,output/'captions.ass',1080,1920,64,900,'bold',
                           caption={'words_per_cue':3,'position':'center','font':'DejaVu Sans','font_size':36})
    expression='+'.join(f'between(T,{a:.4f},{b:.4f})' for a,b in plan['ranges'])
    cw,ch=plan['panel_size'];first=plan['tracks'][0]['crops']
    filters=["[0:v]sendcmd=f=crops.cmd,split=4[l][r][b][f]",
      f'[l]crop@p0={cw}:{ch}:{first[0][0]}:{first[0][1]},scale=1080:960[top]',
      f'[r]crop@p1={cw}:{ch}:{first[1][0]}:{first[1][1]},scale=1080:960[bottom]',
      '[top][bottom]vstack=inputs=2[dual]',
      '[b]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:2[bg]',
      '[f]scale=1080:1920:force_original_aspect_ratio=decrease[fg]',
      '[bg][fg]overlay=(W-w)/2:(H-h)/2[whole]',
      f"[dual][whole]blend=all_expr='if(gt({expression},0),A,B)',subtitles=captions.ass,setsar=1,format=yuv420p[v]"]
    (output/'render.ffscript').write_text(';\n'.join(filters))
    video=output/'dual-face-NOT-APPROVED.mp4'
    import subprocess
    command=['ffmpeg','-y','-hide_banner','-loglevel','verbose','-i',str(source.resolve()),
             '-filter_complex_threads','1','-filter_complex_script','render.ffscript','-map','[v]','-map','0:a:0',
             '-af','loudnorm=I=-14:TP=-1.5:LRA=11','-c:v','libx264','-preset','veryfast','-crf','20','-threads','2',
             '-c:a','aac','-b:a','160k','-movflags','+faststart',str(video.resolve())]
    process=subprocess.run(command,cwd=output,capture_output=True,timeout=600)
    (output/'ffmpeg.log').write_bytes(process.stderr)
    process.check_returncode()
    save(output/'command-report.json',validate_crop_replies(process.stderr.decode(errors='replace'),len(commands)))
    write_srt(words,0,duration,video.with_suffix('.srt'),group_size=3)
    return video
