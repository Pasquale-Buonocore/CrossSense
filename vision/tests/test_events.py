import unittest
from vision.events import CrossingEvents


def person(zone, key=1, x=50):
    return dict(id=key,zone=zone,**{'class':'pedestrian'},bbox=[x-5,20,x+5,60])


class EventTests(unittest.TestCase):
    def test_waiting_excludes_pedestrians_arriving_from_crossing(self):
        e=CrossingEvents()
        e.update(1,0,[person('waiting_left',1),person('crossing',2)],100,100)
        self.assertEqual(e.snapshot()['waiting'],{'waiting_left':1,'waiting_right':0})
        e.update(1,100,[person('crossing',1),person('waiting_right',2),person('waiting_right',3)],100,100)
        self.assertEqual(e.snapshot()['waiting'],{'waiting_left':0,'waiting_right':1})
        e.update(1,200,[person('waiting_right',1),person('waiting_right',2),person('waiting_right',3)],100,100)
        self.assertEqual(e.snapshot()['waiting'],{'waiting_left':0,'waiting_right':1})
        e.update(1,300,[person('waiting_left',1)],100,100)
        self.assertEqual(e.snapshot()['waiting'],{'waiting_left':0,'waiting_right':0})
        e.update(2,0,[person('waiting_right',1)],100,100)
        self.assertEqual(e.snapshot()['waiting'],{'waiting_left':0,'waiting_right':1})
        e.update(2,100,[person('outside',2)],100,100)
        e.update(2,200,[person('crossing',2)],100,100)
        e.update(2,300,[person('waiting_left',2)],100,100)
        self.assertEqual(e.snapshot()['waiting'],{'waiting_left':0,'waiting_right':0})

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

    def test_tracks_first_seen_on_crossing_count_at_either_exit(self):
        for destination,direction in [('waiting_right','left_to_right'),('waiting_left','right_to_left')]:
            with self.subTest(destination=destination):
                e=CrossingEvents()
                e.update(1,0,[person('crossing')],100,100)
                e.update(1,200,[person(destination)],100,100)
                e.update(1,349,[person(destination)],100,100)
                self.assertEqual(e.snapshot()['completed'],0)
                self.assertEqual(e.snapshot()['waiting'],{'waiting_left':0,'waiting_right':0})
                e.update(1,350,[person(destination)],100,100)
                e.update(1,500,[person(destination)],100,100)
                e.update(1,600,[person('crossing')],100,100)
                e.update(1,800,[person(destination)],100,100)
                e.update(1,1000,[person(destination)],100,100)
                result=e.snapshot()
                self.assertEqual(result['completed'],1)
                self.assertEqual(result[direction],1)
                self.assertEqual(result['events'][0]['direction'],direction)
                self.assertEqual(result['events'][0]['track_id'],1)
                self.assertEqual(result['events'][0]['video_ms'],350)
                self.assertEqual(result['wait_samples'],0)
                self.assertIsNone(result['average_wait_ms'])

    def test_return_to_origin_counts_as_exit_without_becoming_waiting(self):
        e=CrossingEvents()
        for t,z in [(0,'waiting_left'),(100,'crossing'),(200,'waiting_left')]:
            e.update(1,t,[person(z)],100,100)
        self.assertEqual(e.snapshot()['completed'],0)
        self.assertEqual(e.snapshot()['waiting']['waiting_left'],0)
        e.update(1,350,[person('waiting_left')],100,100)
        self.assertEqual(e.snapshot()['right_to_left'],1)
        self.assertEqual(e.snapshot()['waiting']['waiting_left'],0)
        self.assertEqual(e.snapshot()['average_wait_ms'],100)

    def test_exit_confirmation_restarts_when_side_changes(self):
        e=CrossingEvents()
        for t,z in [(0,'crossing'),(200,'waiting_left'),(300,'waiting_right'),(449,'waiting_right')]:
            e.update(1,t,[person(z)],100,100)
        self.assertEqual(e.snapshot()['completed'],0)
        e.update(1,450,[person('waiting_right')],100,100)
        self.assertEqual(e.snapshot()['left_to_right'],1)
        self.assertEqual(e.snapshot()['right_to_left'],0)

    def test_exit_confirmation_restarts_on_crossing_or_outside(self):
        for interruption in ('crossing','outside'):
            with self.subTest(interruption=interruption):
                e=CrossingEvents()
                for t,z in [(0,'crossing'),(200,'waiting_left'),(300,interruption),
                            (400,'waiting_left'),(549,'waiting_left')]:
                    e.update(1,t,[person(z)],100,100)
                self.assertEqual(e.snapshot()['completed'],0)
                e.update(1,550,[person('waiting_left')],100,100)
                self.assertEqual(e.snapshot()['completed'],1)

    def test_missing_crossing_expired_tracks_and_invalid_data_do_not_count(self):
        sequences=[[(0,'waiting_left'),(200,'waiting_right'),(400,'waiting_right')],
                   [(0,'crossing'),(3000,'waiting_right'),(3200,'waiting_right')]]
        for sequence in sequences:
            e=CrossingEvents()
            for t,z in sequence:e.update(1,t,[person(z)],100,100)
            self.assertEqual(e.snapshot()['completed'],0)
        e=CrossingEvents();e.update(1,0,[person('waiting_left')],100,100)
        e.update(1,100,[person('crossing')],100,100,False)
        e.update(1,200,[person('waiting_right')],100,100)
        self.assertEqual(e.snapshot()['completed'],0)

    def test_changed_id_or_stream_cannot_complete_previous_track(self):
        for stream,key in [(1,2),(2,1)]:
            with self.subTest(stream=stream,key=key):
                e=CrossingEvents()
                e.update(1,0,[person('crossing')],100,100)
                e.update(stream,200,[person('waiting_right',key)],100,100)
                e.update(stream,400,[person('waiting_right',key)],100,100)
                self.assertEqual(e.snapshot()['completed'],0)

    def test_bicycle_exit_counts_but_vehicle_exit_does_not(self):
        for object_class,expected in [('bicycle',1),('vehicle',0)]:
            with self.subTest(object_class=object_class):
                e=CrossingEvents()
                for t,z in [(0,'crossing'),(100,'waiting_right'),(250,'waiting_right')]:
                    detection=person(z)
                    detection['class']=object_class
                    e.update(1,t,[detection],100,100)
                self.assertEqual(e.snapshot()['completed'],expected)

    def test_immobility_uses_video_time_and_resets_on_motion(self):
        e=CrossingEvents()
        for t in range(0,3500,500):e.update(1,t,[person('crossing')],100,100)
        self.assertEqual(e.snapshot()['stopped_ids'],[1])
        e.update(1,3500,[person('crossing',x=70)],100,100)
        self.assertEqual(e.snapshot()['stopped_ids'],[])
