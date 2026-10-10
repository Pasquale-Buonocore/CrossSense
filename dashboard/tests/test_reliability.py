import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rt import RTService
from test_rt import frame, state
from vision.pipeline import VisionService
from vision.zones import ZoneStore


class ReliabilityTests(unittest.TestCase):
    def test_click_during_rpc_and_reset_is_queued_for_next_edge(self):
        sent=[]
        rt=RTService(lambda m,p:json.dumps(state(json.loads(p)['frame'])))
        rt.publish(frame());rt.exchange()
        rt.request('pedestrian','first')
        def click_in_call(m,p):
            sent.append(json.loads(p))
            self.assertTrue(rt.in_flight)
            self.assertEqual(rt.request('accessible','during-rpc')['status'],'queued')
            return json.dumps(state(sent[-1]['frame']))
        rt.call=click_in_call;rt.publish(frame()|{'frame':2,'time_ms':101});rt.exchange()
        self.assertEqual(rt.seen['first']['status'],'accepted')
        self.assertEqual(rt.seen['during-rpc']['status'],'queued')
        self.assertEqual(rt.request('vehicle_priority','during-reset')['status'],'queued')
        rt.call=lambda m,p:(sent.append(json.loads(p)) or json.dumps(state(sent[-1]['frame'])))
        rt.publish(frame()|{'frame':3,'time_ms':102});rt.exchange()
        self.assertEqual(sent[-1]['requests'],[False]*3)
        self.assertEqual(rt.seen['during-rpc']['status'],'queued')
        rt.publish(frame()|{'frame':4,'time_ms':103});rt.exchange()
        self.assertEqual(sent[-1]['requests'],[True,True,True])
        self.assertEqual(rt.seen['during-rpc']['status'],'accepted')
        self.assertEqual(rt.seen['during-reset']['status'],'accepted')

    def test_retry_missing_model_keeps_error_visible(self):
        with tempfile.TemporaryDirectory() as folder:
            video=Path(folder)/'input.mp4';video.touch()
            service=VisionService(RTService(),ZoneStore(Path(folder)/'zones.json'),video,Path(folder)/'absent.pt')
            with self.assertRaisesRegex(ValueError,'Modello locale assente'):service.restart()
            self.assertEqual(service.snapshot()['status'],'error')
            self.assertIn('Modello locale assente',service.snapshot()['error'])
            self.assertFalse(service.snapshot()['fresh'])

    def test_no_video_is_idle_without_weights(self):
        with tempfile.TemporaryDirectory() as folder:
            service=VisionService(RTService(),ZoneStore(Path(folder)/'zones.json'))
            service.start()
            self.assertIsNone(service.thread)
            self.assertEqual(service.status,'idle')

    def test_retry_ack_does_not_lose_request_or_repeat_edges(self):
        sent=[]; fail=[False]
        def call(m,p):
            sent.append(json.loads(p))
            if fail[0]: raise RuntimeError('lost response')
            return json.dumps(state(sent[-1]['frame']))
        rt=RTService(call);rt.publish(frame());rt.exchange()
        rt.request('pedestrian','one');rt.publish(frame()|{'frame':2,'time_ms':101})
        fail[0]=True;rt.exchange()
        fail[0]=False;rt.exchange()
        self.assertEqual(sent[-1]['frame'],sent[-2]['frame'])
        self.assertEqual(rt.seen['one']['status'],'accepted')
        self.assertEqual(rt.requests,[False]*3)
        rt.exchange();self.assertEqual(sent[-1]['requests'],[True,False,False])
        rt.publish(frame()|{'frame':3,'time_ms':102});rt.exchange()
        self.assertEqual(sent[-1]['requests'],[False]*3)
        self.assertFalse(rt.lowering)

    def test_new_source_cancels_requests_and_discards_old_reply(self):
        rt=RTService(lambda m,p:json.dumps(state(json.loads(p)['frame'])))
        rt.publish(frame());rt.exchange();rt.request('pedestrian','one')
        def switch(m,p):
            rt.publish(frame()|{'stream':8})
            return json.dumps(state(json.loads(p)['frame']))
        before=rt.received;rt.call=switch;rt.exchange()
        self.assertEqual(rt.received,before)
        self.assertEqual(rt.seen['one']['status'],'cancelled')

    def test_reboot_cancels_requests_and_resets_stream(self):
        rt=RTService(lambda m,p:json.dumps(state(json.loads(p)['frame'])))
        rt.exchange();rt.request('pedestrian','one');stream=rt.stream
        rt.call=lambda m,p:json.dumps(state(json.loads(p)['frame'])|{'uptime_ms':1})
        rt.exchange()
        self.assertNotEqual(rt.stream,stream)
        self.assertEqual(rt.seen['one']['status'],'cancelled')
