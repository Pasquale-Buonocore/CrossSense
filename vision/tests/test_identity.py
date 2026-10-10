import unittest
from vision.identity import IdentityTracker, deduplicate_users


def detection(raw,x,y=50):
    return dict(id=raw,**{'class':'pedestrian'},bbox=[x-5,y-10,x+5,y+10])


class IdentityTests(unittest.TestCase):
    def test_partial_box_shift_keeps_a_recent_confirmed_tracker_id(self):
        tracker=IdentityTracker()
        first=tracker.update([detection(1,30)],0,100,100)[0]['id']
        shifted=tracker.update([detection(1,38)],.033,100,100)[0]['id']
        self.assertEqual(first,shifted)

    def test_rider_is_one_participant_but_separate_bicycle_is_preserved(self):
        p=detection(1,50)
        bike=detection(2,50);bike['class']='bicycle'
        separate=detection(3,80);separate['class']='bicycle'
        self.assertEqual([d['id'] for d in deduplicate_users([p,bike,separate])],[1,3])
    def test_short_loss_new_raw_id_preserves_motion_identity(self):
        tracker=IdentityTracker()
        original=tracker.update([detection(1,20)],0,100,100)[0]['id']
        for i in range(1,6):tracker.update([detection(1,20+i)],i*.1,100,100)
        result=tracker.update([detection(8,28)],.8,100,100)
        self.assertEqual(result[0]['id'],original)
        self.assertEqual(result[0]['tracker_id'],8)

    def test_teleport_and_long_loss_never_reuse_identity(self):
        tracker=IdentityTracker()
        first=tracker.update([detection(1,10)],0,100,100)[0]['id']
        second=tracker.update([detection(1,90)],.1,100,100)[0]['id']
        self.assertNotEqual(first,second)
        third=tracker.update([detection(1,90)],3,100,100)[0]['id']
        self.assertNotEqual(second,third)

    def test_two_opposite_trajectories_stay_distinct(self):
        tracker=IdentityTracker();ids=None
        for i in range(10):
            out=tracker.update([detection(1,30+i,45),detection(2,50-i,55)],i*.1,100,100)
            current=[d['id'] for d in out]
            if ids is None:ids=current
            self.assertEqual(current,ids)
        tracker.reset()
        self.assertEqual(tracker.update([detection(9,20)],0,100,100)[0]['id'],1)
