import unittest
from vision.events import CrossingEvents


def person(zone, key=1, x=50):
    return dict(id=key,zone=zone,**{'class':'pedestrian'},bbox=[x-5,20,x+5,60])


class EventTests(unittest.TestCase):
    def test_complete_directions_dedup_and_replay_reset(self):
        e=CrossingEvents()
        for key,origin,destination in [(1,'waiting_left','waiting_right'),(2,'waiting_right','waiting_left')]:
            for t,z in [(0,origin),(1000,'crossing'),(2000,destination),(2200,destination),(2400,destination)]:
                e.update(1,t,[person(z,key)],100,100)
        self.assertEqual(e.snapshot()['completed'],2)
        self.assertEqual(e.snapshot()['left_to_right'],1)
        self.assertEqual(e.snapshot()['right_to_left'],1)
        self.assertEqual(e.snapshot()['average_wait_ms'],1000)
        e.update(2,0,[person('waiting_left')],100,100)
        e.update(2,100,[person('crossing')],100,100)
        e.update(2,200,[person('waiting_right')],100,100)
        e.update(2,400,[person('waiting_right')],100,100)
        self.assertEqual(e.snapshot()['completed'],3)

    def test_returns_missing_ids_invalid_data_and_partial_tracks_do_not_count(self):
        sequences=[[(0,'crossing'),(200,'waiting_right'),(400,'waiting_right')],
                   [(0,'waiting_left'),(100,'crossing'),(200,'waiting_left'),(400,'waiting_right'),(600,'waiting_right')],
                   [(0,'waiting_left'),(100,'crossing'),(3000,'waiting_right'),(3200,'waiting_right')]]
        for sequence in sequences:
            e=CrossingEvents()
            for t,z in sequence:e.update(1,t,[person(z)],100,100)
            self.assertEqual(e.snapshot()['completed'],0)
        e=CrossingEvents();e.update(1,0,[person('waiting_left')],100,100)
        e.update(1,100,[person('crossing')],100,100,False)
        e.update(1,200,[person('waiting_right')],100,100)
        self.assertEqual(e.snapshot()['completed'],0)

    def test_immobility_uses_video_time_and_resets_on_motion(self):
        e=CrossingEvents()
        for t in range(0,3500,500):e.update(1,t,[person('crossing')],100,100)
        self.assertEqual(e.snapshot()['stopped_ids'],[1])
        e.update(1,3500,[person('crossing',x=70)],100,100)
        self.assertEqual(e.snapshot()['stopped_ids'],[])
