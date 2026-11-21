"""Conservative packet timing gate; does not verify perceptual A/V sync."""
import json
import math
import subprocess


def analyze(packets,streams):
    issues=[];summary={}
    for stream in streams:
        kind=stream.get('codec_type')
        if kind not in ('audio','video'):continue
        rows=[p for p in packets if p.get('stream_index')==stream['index']]
        times=[];previous_dts=None
        try:
            for row in rows:
                pts,dts,duration=(float(row[k]) for k in ('pts_time','dts_time','duration_time'))
                if not all(math.isfinite(x) for x in (pts,dts,duration)) or duration<=0:
                    raise ValueError()
                if previous_dts is not None and dts<=previous_dts:
                    issues.append({'code':'NON_MONOTONIC_DTS','stream':kind})
                previous_dts=dts
                times.append((pts,pts+duration))
        except (KeyError,TypeError,ValueError):
            issues.append({'code':'INVALID_PACKET_TIMING','stream':kind});continue
        if not times:
            issues.append({'code':'EMPTY_PACKET_STREAM','stream':kind});continue
        times.sort();max_gap=max_overlap=0
        for previous,current in zip(times,times[1:]):
            max_gap=max(max_gap,current[0]-previous[1])
            max_overlap=max(max_overlap,previous[1]-current[0])
        # AAC priming may start before zero; do not mistake it for desync.
        summary[kind]={'packets':len(rows),'start_seconds':max(0,times[0][0]),
                       'end_seconds':max(t[1] for t in times),
                       'max_gap_seconds':round(max_gap,6),'max_overlap_seconds':round(max_overlap,6)}
        if max_gap>.1:issues.append({'code':'PACKET_GAP','stream':kind})
        if max_overlap>.001:issues.append({'code':'PACKET_OVERLAP','stream':kind})
    if not all(k in summary for k in ('audio','video')):
        issues.append({'code':'MISSING_AV_TIMING'})
    else:
        for boundary in ('start_seconds','end_seconds'):
            if abs(summary['audio'][boundary]-summary['video'][boundary])>.1:
                issues.append({'code':'AV_BOUNDARY_DIFFERENCE','boundary':boundary})
    # Report counts rather than thousands of duplicate packet errors.
    distinct=[dict(item) for item in {tuple(sorted(i.items())) for i in issues}]
    distinct.sort(key=lambda item:json.dumps(item,sort_keys=True))
    return {'schema':1,'scope':'EXPORTED_PACKET_TIMING_ONLY','passed':not issues,
            'streams':summary,'issues':distinct,'perceptual_sync_verified':False,
            'editorial_approved':False,'policy':{'max_gap_seconds':.1,
                'max_overlap_seconds':.001,'max_av_boundary_difference_seconds':.1}}


def audit(path):
    try:
        result=subprocess.run(['ffprobe','-v','error','-read_intervals','%+#20000',
            '-show_packets','-show_streams','-show_entries',
            'packet=stream_index,pts_time,dts_time,duration_time:stream=index,codec_type',
            '-of','json',str(path)],capture_output=True,check=True,timeout=30)
        if len(result.stdout)>8*1024*1024:raise ValueError('PROBE_SIZE_LIMIT')
        data=json.loads(result.stdout)
        packets=data['packets']
        if len(packets)>=20000:raise ValueError('PACKET_LIMIT')
        return analyze(packets,data['streams'])
    except (subprocess.SubprocessError,OSError,ValueError,KeyError,TypeError):
        return {'schema':1,'scope':'EXPORTED_PACKET_TIMING_ONLY','passed':False,
                'issues':[{'code':'TIMELINE_PROBE_FAILED'}],'perceptual_sync_verified':False,
                'editorial_approved':False}
