import unittest
from nuvem.framing import visible_fraction, panel_crop, plan_dual, crops_at, coverage, validate_crop_replies


def samples(count=16):
    return [{'t':i/4,'faces':[[200+i*2,100,80,100],[800+i*2,120,90,110]]} for i in range(count)]


class FramingTests(unittest.TestCase):
    def test_fraction_full_partial_and_missing(self):
        face=[10,10,20,20]
        self.assertEqual(visible_fraction(face,[0,0,40,40]),1)
        self.assertEqual(visible_fraction(face,[10,10,10,20]),.5)
        self.assertEqual(visible_fraction(face,[50,50,10,10]),0)
        self.assertEqual(visible_fraction([0,0,0,20],[0,0,50,50]),0)

    def test_plan_preserves_both_faces_and_stays_in_frame(self):
        data=samples();plan=plan_dual(data,1280,720)
        self.assertEqual(plan['status'],'DUAL_FACE_DIAGNOSTIC')
        for sample in data:
            crops=crops_at(plan,sample['t'],1280,720)
            self.assertEqual(len(crops),2)
            for x,y,w,h in crops:
                self.assertGreaterEqual(x,0);self.assertGreaterEqual(y,0)
                self.assertLessEqual(x+w,1280);self.assertLessEqual(y+h,720)
            self.assertTrue(all(any(visible_fraction(face,crop)>=.95 for crop in crops) for face in sample['faces']))
        self.assertFalse(plan['active_speaker_verified'])
        self.assertFalse(plan['person_identity_verified'])

    def test_one_face_or_crowd_does_not_invent_two_subjects(self):
        for data in ([{'t':i/4,'faces':[[i*10,100,80,100]]} for i in range(20)],
                     [{'t':i/4,'faces':[[20,20,30,30],[200,20,30,30],[800,20,30,30]]} for i in range(20)]):
            self.assertEqual(plan_dual(data,1280,720)['status'],'INSUFFICIENT_TWO_FACE_EVIDENCE')

    def test_short_evidence_and_too_close_faces_rejected(self):
        self.assertEqual(plan_dual(samples(5),1280,720)['status'],'INSUFFICIENT_TWO_FACE_EVIDENCE')
        data=[{'t':i/4,'faces':[[200,100,160,160],[365,100,160,160]]} for i in range(16)]
        self.assertNotEqual(plan_dual(data,1280,720)['status'],'DUAL_FACE_DIAGNOSTIC')

    def test_long_detection_gap_preserves_whole_frame(self):
        data=samples()+[{'t':10+i/4,'faces':[[200,100,80,100],[800,120,90,110]]} for i in range(8)]
        plan=plan_dual(data,1280,720)
        self.assertEqual(crops_at(plan,6,1280,720),[[0,0,1280,720]])
        self.assertEqual(crops_at(plan,20,1280,720),[[0,0,1280,720]])

    def test_coverage_counts_both_faces_not_only_the_largest(self):
        data=samples()
        old=coverage(data,lambda t:[[650,0,404,720]])
        plan=plan_dual(data,1280,720)
        new=coverage(data,lambda t:crops_at(plan,t,1280,720))
        self.assertEqual(old['face_visibility_ratio'],.5)
        self.assertEqual(old['both_faces_visibility_ratio'],0)
        self.assertEqual(new['face_visibility_ratio'],1)
        self.assertEqual(new['both_faces_visibility_ratio'],1)

    def test_no_detections_is_unknown_not_success(self):
        result=coverage([{'t':0,'faces':[]}],lambda t:[[0,0,1280,720]])
        self.assertIsNone(result['face_visibility_ratio'])
        self.assertIsNone(result['both_faces_visibility_ratio'])
        self.assertEqual(result['samples_without_detection'],1)

    def test_crop_motion_is_interpolated(self):
        plan=plan_dual(samples(),1280,720)
        a=crops_at(plan,2.0,1280,720);b=crops_at(plan,2.25,1280,720);mid=crops_at(plan,2.125,1280,720)
        for i in range(2):self.assertAlmostEqual(mid[i][0],(a[i][0]+b[i][0])/2,delta=1)

    def test_ignored_filter_commands_cannot_pass_diagnostic(self):
        good='Command reply for command #0: ret:Success res:\n'
        self.assertEqual(validate_crop_replies(good*10,10)['successful_replies'],10)
        for log in ('',good*2,good*9+'Command reply for command #0: ret:Option not found res:\n'):
            with self.assertRaisesRegex(RuntimeError,'FFMPEG_CROP_COMMAND_FAILED'):
                validate_crop_replies(log,10)
