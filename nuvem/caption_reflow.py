"""Plan readable cues without changing speech, then export one plan to ASS and SRT."""
import math
from decimal import Decimal,ROUND_CEILING,ROUND_FLOOR
from pathlib import Path
from .caption_audit import audit,POLICY
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
    if type(duration) not in (int,float) or not math.isfinite(duration) or duration<=0:
        raise ValueError('INVALID_REFLOW_DURATION')
    previous=0
    for w in words:
        if not isinstance(w.get('word'),str) or not w['word'].strip() or any(c in w['word'] for c in '\n\r<>'):
            raise ValueError('INVALID_REFLOW_TEXT')
        if not all(type(w.get(k)) in (int,float) and math.isfinite(w[k]) for k in ('start','end')) or not previous-.001<=w['start']<w['end']<=duration+.05:
            raise ValueError('INVALID_REFLOW_TIMING')
        previous=w['end']
    # ASS is centisecond based. Plan on that grid so ASS/SRT timings agree.
    tolerance=POLICY['alignment_tolerance_seconds']
    tolerance_decimal=Decimal(str(tolerance));duration_decimal=Decimal(str(duration))
    def tick(value,up=False):
        return int((value*100).to_integral_value(rounding=ROUND_CEILING if up else ROUND_FLOOR))
    count=len(words);states={0:{0:(0,[])}}
    for i in range(count):
        if i not in states:continue
        for j in range(i+1,min(count,i+8)+1):
            group=words[i:j];lines=lines_for(group)
            if not lines or any(b['start']-a['end']>1.2 for a,b in zip(group,group[1:])):continue
            first,last=group[0]['start'],group[-1]['end']
            first_decimal,last_decimal=Decimal(str(first)),Decimal(str(last))
            start_min=max(0,tick(first_decimal-tolerance_decimal,True));start_max=tick(first_decimal)
            end_min=tick(last_decimal,True);end_max=min(tick(last_decimal+tolerance_decimal),tick(duration_decimal))
            text='\n'.join(lines);characters=len(' '.join(lines))
            needed=max(tick(Decimal(str(POLICY['min_cue_seconds'])),True),
                       int((Decimal(characters*100)/Decimal(str(POLICY['max_cps']))).to_integral_value(rounding=ROUND_CEILING)))
            for prior_end,(prior_cost,prior_cues) in tuple(states[i].items()):
                for start in range(max(start_min,prior_end),start_max+1):
                    end=max(end_min,start+needed)
                    if end>end_max or end-start>400:continue
                    lead=first-start/100;lag=end/100-last
                    cost=prior_cost+100*((len(group)-3)**2+1)+5*round((lead+lag)*100)
                    old=states.setdefault(j,{}).get(end)
                    if old is None or cost<old[0]:
                        cue={'start':start/100,'end':end/100,'text':text,'word_range':[i,j]}
                        states[j][end]=(cost,prior_cues+[cue])
    choices=states.get(count,{}) if count else {}
    cues=min(choices.values(),key=lambda x:x[0])[1] if choices else []
    return {'schema':1,'status':'PLANNED' if cues else 'NO_READABLE_PLAN','cues':cues,'word_count':count,
            'speech_modified':False,'word_timestamps_modified':False,'editorial_approved':False,
            'display_tolerance_seconds':tolerance,
            'max_display_lead_seconds':round(max((words[c['word_range'][0]]['start']-c['start'] for c in cues),default=0),4),
            'max_display_lag_seconds':round(max((c['end']-words[c['word_range'][1]-1]['end'] for c in cues),default=0),4)}


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
