"""Plan readable cues without changing speech, then export one plan to ASS and SRT."""
import math
from pathlib import Path
from .caption_audit import audit
from .engine import ass_escape,ass_time,save


def lines_for(words):
    lines=['']
    for word in words:
        text=word['word'].strip()
        if len(text)>32:return None
        if len(lines[-1])+bool(lines[-1])+len(text)>32:lines.append(text)
        else:lines[-1]+=(' ' if lines[-1] else '')+text
    return lines if len(lines)<=2 else None


def plan(words,duration):
    previous=0
    for w in words:
        if not isinstance(w.get('word'),str) or not w['word'].strip() or any(c in w['word'] for c in '\n\r<>'):
            raise ValueError('INVALID_REFLOW_TEXT')
        if not all(type(w.get(k)) in (int,float) and math.isfinite(w[k]) for k in ('start','end')) or not previous-.001<=w['start']<w['end']<=duration+.05:
            raise ValueError('INVALID_REFLOW_TIMING')
        previous=w['end']
    count=len(words);best={count:(0,[])}
    for i in range(count-1,-1,-1):
        choices=[]
        for j in range(i+1,min(count,i+8)+1):
            group=words[i:j];span=group[-1]['end']-group[0]['start'];lines=lines_for(group)
            if j not in best or not lines or span>4 or any(b['start']-a['end']>1.2 for a,b in zip(group,group[1:])):continue
            text='\n'.join(lines)
            if span<.3 or len(' '.join(lines))/span>25:continue
            cue={'start':group[0]['start'],'end':group[-1]['end'],'text':text,'word_range':[i,j]}
            # Prefer small stable groups, then fewer cues; never relax constraints.
            cost=(len(group)-3)**2+1+best[j][0]
            choices.append((cost,[cue]+best[j][1]))
        if choices:best[i]=min(choices,key=lambda x:x[0])
    return {'schema':1,'status':'PLANNED' if count and 0 in best else 'NO_READABLE_PLAN',
            'cues':best[0][1] if count and 0 in best else [],'word_count':count,
            'speech_modified':False,'editorial_approved':False}


def srt_time(seconds):
    ms=round(seconds*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


def write(words,duration,ass_path,srt_path,center=True):
    result=plan(words,duration)
    save(ass_path.with_suffix('.plan.json'),result)
    if result['status']!='PLANNED':raise ValueError('NO_READABLE_CAPTION_PLAN')
    srt='\n'.join(f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['text']}\n" for i,c in enumerate(result['cues'],1))
    checked=audit(srt,duration,words)
    if not checked['passed']:raise ValueError('REFLOW_AUDIT_REJECTED')
    header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
'''
    header+=f'Style: Cap,DejaVu Sans,52,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,{5 if center else 2},80,80,{0 if center else 260},1\n'
    header+='[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'
    events=[]
    for cue in result['cues']:
        text=r'\N'.join(ass_escape(line) for line in cue['text'].splitlines())
        events.append(f"Dialogue: 0,{ass_time(cue['start'])},{ass_time(cue['end'])},Cap,,0,0,0,,{text}")
    ass_path.write_text(header+'\n'.join(events)+'\n',encoding='utf-8')
    srt_path.write_text(srt,encoding='utf-8')
    return checked
