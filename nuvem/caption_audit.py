"""Subtitle export integrity/readability gates, not speech or editorial approval."""
import math
import re
import sys
import unicodedata
from pathlib import Path
from .engine import digest, probe, save

POLICY={'max_cps':25,'min_cue_seconds':.30,'max_lines':2,'max_line_characters':42,
        'alignment_tolerance_seconds':.15}
STAMP=re.compile(r'^(\d{2,}):([0-5]\d):([0-5]\d),(\d{3}) --> (\d{2,}):([0-5]\d):([0-5]\d),(\d{3})$')


def tokens(text):
    return re.findall(r'[^\W_]+',unicodedata.normalize('NFKC',text).casefold())


def parse_srt(text):
    text=text.lstrip('\ufeff').replace('\r\n','\n').replace('\r','\n').strip()
    if not text:raise ValueError('EMPTY_SRT')
    cues=[]
    for block in re.split(r'\n[ \t]*\n',text):
        lines=block.splitlines()
        if len(lines)<3 or lines[0]!=str(len(cues)+1):raise ValueError('INVALID_SRT_BLOCK')
        match=STAMP.fullmatch(lines[1])
        if not match:raise ValueError('INVALID_SRT_TIMESTAMP')
        def seconds(parts):
            h,m,s,ms=map(int,parts);return h*3600+m*60+s+ms/1000
        body='\n'.join(lines[2:])
        if not body.strip() or not tokens(body):raise ValueError('EMPTY_SRT_TEXT')
        # Unsupported markup could make measured and displayed text disagree.
        if re.search(r'[<>\x00-\x08\x0b\x0c\x0e-\x1f]',body):raise ValueError('UNSUPPORTED_SRT_MARKUP')
        cues.append({'start':seconds(match.groups()[:4]),'end':seconds(match.groups()[4:]),'text':body})
    return cues


def audit(text,duration,reference_words=None):
    if type(duration) not in (int,float) or not math.isfinite(duration) or duration<=0:
        raise ValueError('INVALID_MEDIA_DURATION')
    result={'schema':1,'scope':'SUBTITLE_EXPORT_INTEGRITY_AND_READABILITY_ONLY','policy':dict(POLICY),
            'passed':False,'editorial_approved':False,'speech_accuracy_verified':False,
            'reference_match':'NOT_CHECKED','issues':[],'cue_count':0}
    try:cues=parse_srt(text)
    except ValueError as error:
        result['issues'].append({'code':str(error)});return result
    result['cue_count']=len(cues);previous_end=0;flattened=[];bounds=[];rates=[]
    def issue(code,index,**details):result['issues'].append({'code':code,'cue':index,**details})
    for i,cue in enumerate(cues,1):
        span=cue['end']-cue['start'];body=cue['text'];lines=body.splitlines()
        if not 0<=cue['start']<cue['end']<=duration+.05:issue('CUE_OUT_OF_BOUNDS',i)
        if cue['start']<previous_end-.001:issue('OVERLAPPING_CUES',i)
        previous_end=max(previous_end,cue['end'])
        if span<POLICY['min_cue_seconds']:issue('CUE_TOO_BRIEF',i,duration_seconds=round(span,3))
        cps=len(' '.join(lines))/span if span>0 else None
        if cps is not None:
            rates.append(cps)
            if cps>POLICY['max_cps']:issue('READING_SPEED_EXCEEDED',i,characters_per_second=round(cps,3))
        if len(lines)>POLICY['max_lines'] or any(len(line)>POLICY['max_line_characters'] for line in lines):issue('TEXT_LAYOUT_EXCEEDED',i)
        first=len(flattened);flattened.extend(tokens(body));bounds.append((first,len(flattened),cue))
    result['max_cps']=round(max(rates),3) if rates else None
    if reference_words is not None:
        reference=[]
        for word in reference_words:
            a,b=word.get('start'),word.get('end')
            if not isinstance(word.get('word'),str) or not all(type(t) in (int,float) and math.isfinite(t) for t in (a,b)) or not 0<=a<b<=duration+.05:
                result['issues'].append({'code':'INVALID_REFERENCE_WORD'});return result
            reference.extend((token,a,b) for token in tokens(word['word']))
        result['reference_token_count']=len(reference);result['export_token_count']=len(flattened)
        match=bool(reference) and flattened==[w[0] for w in reference]
        result['reference_match']='MATCH' if match else 'MISMATCH'
        if not match:result['issues'].append({'code':'TRANSCRIPT_EXPORT_MISMATCH'})
        else:
            tolerance=POLICY['alignment_tolerance_seconds']
            for i,(a,b,cue) in enumerate(bounds,1):
                if abs(cue['start']-reference[a][1])>tolerance or abs(cue['end']-reference[b-1][2])>tolerance:issue('TRANSCRIPT_TIMING_MISMATCH',i)
    result['passed']=not result['issues']
    return result


def audit_outputs(source,project,upstream,output,outputs):
    """Bind subtitles to selected/remapped ASR words; never trust a sidecar alone."""
    from .framing_stage import selected_segment
    accepted=[];reports=[]
    for relative in outputs:
        video=(output/relative).resolve()
        if not video.is_relative_to(output.resolve()) or not video.is_file():raise ValueError('CAPTION_OUTPUT_PATH_REJECTED')
        try:
            segment,words,_=selected_segment(video,source,project)
            sys.path.insert(0,str(upstream))
            import tighten
            keeps=tighten.plan_cuts(words,segment['start'],segment['end'])
            mapped,expected=tighten.remap_words(words,segment['start'],keeps)
            duration=float(probe(video)['format']['duration'])
            sidecar=video.with_suffix('.srt')
            if sidecar.is_symlink():raise ValueError('SRT_SYMLINK_REJECTED')
            result=audit(sidecar.read_text(encoding='utf-8-sig'),duration,mapped)
            result['srt_sha256']=digest(sidecar)
            result['transcript_sha256']=digest(project/'transcript.json')
            if abs(duration-expected)>.35:
                result['issues'].append({'code':'RETIMED_MEDIA_DURATION_MISMATCH'});result['passed']=False
        except (ValueError,FileNotFoundError,UnicodeError) as error:
            result={'passed':False,'issues':[{'code':'CAPTION_INPUT_REJECTED','reason':str(error)}],
                    'editorial_approved':False,'speech_accuracy_verified':False}
        result.update(video=relative,video_sha256=digest(video))
        reports.append(result)
        if result['passed']:accepted.append(relative)
    report={'scope':'SUBTITLE_EXPORT_INTEGRITY_AND_READABILITY_ONLY','items':reports,
            'editorial_approved':False,'publication_approved':False}
    save(output/'caption_report.json',report)
    return accepted,report
