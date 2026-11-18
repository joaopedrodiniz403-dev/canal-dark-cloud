"""Read-only capability preflight; does not install packages or validate editorial quality."""
import json
import shutil
import subprocess


def inspect():
    missing=[]
    def output(program,*args):
        if not shutil.which(program):
            missing.append(program);return ''
        try:
            result=subprocess.run([program,*args],capture_output=True,text=True,timeout=15)
        except (OSError,subprocess.TimeoutExpired):
            missing.append(program+':inspection-failed');return ''
        if result.returncode:missing.append(program+':inspection-failed')
        return result.stdout
    def names(text):return {line.split()[1] for line in text.splitlines() if len(line.split())>=2}
    filters=names(output('ffmpeg','-hide_banner','-filters'))
    encoders=names(output('ffmpeg','-hide_banner','-encoders'))
    decoders=names(output('ffmpeg','-hide_banner','-decoders'))
    for capability in ('subtitles','drawtext'):
        if capability not in filters:missing.append('filter:'+capability)
    for capability in ('libx264','aac'):
        if capability not in encoders:missing.append('encoder:'+capability)
    for capability in ('h264','vp9','opus'):
        if capability not in decoders:missing.append('decoder:'+capability)
    output('ffprobe','-version')
    if 'DejaVu Sans' not in [x.strip() for x in output('fc-match','--format','%{family}','DejaVu Sans').split(',')]:
        missing.append('font:DejaVu Sans')
    return {'scope':'FFMPEG_FONT_CAPABILITIES_ONLY','ready':not missing,'missing':sorted(set(missing))}


if __name__=='__main__':
    result=inspect();print(json.dumps(result,indent=2));raise SystemExit(0 if result['ready'] else 1)
