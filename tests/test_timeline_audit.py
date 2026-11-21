import unittest
from unittest.mock import patch
from nuvem.timeline_audit import analyze,audit

STREAMS=[{'index':0,'codec_type':'video'},{'index':1,'codec_type':'audio'}]
def packet(index,pts,dts=None,duration=.04):
    return {'stream_index':index,'pts_time':str(pts),'dts_time':str(pts if dts is None else dts),'duration_time':str(duration)}

class TimelineTests(unittest.TestCase):
    def test_b_frames_and_aac_priming_are_valid(self):
        packets=[packet(0,.04,-.04),packet(0,0,0),packet(0,.08,.04),
                 packet(1,-.04),packet(1,0),packet(1,.04),packet(1,.08)]
        result=analyze(packets,STREAMS)
        self.assertTrue(result['passed']);self.assertFalse(result['perceptual_sync_verified'])
    def test_corrected_dts_cannot_hide_overlapping_audio(self):
        packets=[packet(0,0),packet(0,.04),packet(1,0),packet(1,.00001)]
        result=analyze(packets,STREAMS)
        self.assertFalse(result['passed'])
        self.assertIn('PACKET_OVERLAP',[i['code'] for i in result['issues']])
    def test_gap_and_av_end_difference_rejected(self):
        result=analyze([packet(0,0),packet(0,.3),packet(1,0)],STREAMS)
        codes=[i['code'] for i in result['issues']]
        self.assertIn('PACKET_GAP',codes);self.assertIn('AV_BOUNDARY_DIFFERENCE',codes)
    def test_missing_invalid_and_non_monotonic_timing_fail_closed(self):
        for packets in ([],[packet(0,float('nan'))],[packet(0,0),packet(0,.04,0)],
                        [{'stream_index':0,'pts_time':'N/A'}]):
            self.assertFalse(analyze(packets,STREAMS)['passed'])
    def test_probe_failure_does_not_approve(self):
        with patch('nuvem.timeline_audit.subprocess.run',side_effect=OSError()):
            self.assertFalse(audit('missing.mp4')['passed'])
