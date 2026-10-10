import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rt import RTService, validate_frame, validate_state


def frame():
    return dict(stream=7,frame=1,time_ms=100,age_ms=0,valid=True,crossing='clear',approach='clear',tracks=[],requests=[False]*3)


def state(n):
    return dict(frame=n,ok=True,error=None,applied_stream=7,applied_frame=n,uptime_ms=100,phase='PED_CLEARANCE',remaining_ms=None,vehicle_light='RED',pedestrian_light='RED',buzzer=False,beacon=False,observation_valid=True,fault=None,alarms=[],estimates=[])


class AdapterTests(unittest.TestCase):
    def test_frames(self):
        validate_frame(frame())
        for change in ({'valid':False},{'tracks':[[1,'pedestrian','crossing',None,None]]},{'tracks':[[1,'other','outside',0,None]]},{'frame':True},{'requests':[0,False,False]}):
            with self.assertRaises(ValueError): validate_frame(frame()|change)

    def test_response(self):
        validate_state(json.dumps(state(1)),1)
        for change in ({'frame':2},{'vehicle_light':'BLUE'},{'estimates':[[1,None,None,-1,None]]},{'ok':False}):
            with self.assertRaises(ValueError): validate_state(json.dumps(state(1)|change),1)

    def test_requests_freshness_and_single_acquisition(self):
        now=[0.0];sent=[]
        def call(method,payload):
            self.assertEqual(method,'crosssense_update')
            f=json.loads(payload);sent.append(f)
            return json.dumps(state(f['frame']))
        rt=RTService(call,lambda:now[0]);rt.publish(frame());rt.exchange()
        self.assertTrue(rt.snapshot()['connected'])
        self.assertEqual(rt.request('accessible','r1')['status'],'queued')
        rt.exchange();self.assertEqual(sent[-1]['requests'],[True,True,False])
        self.assertFalse(sent[-1]['valid']);self.assertIsNone(sent[-1]['time_ms'])
        self.assertEqual(sent[0]['stream'],sent[1]['stream'])
        self.assertEqual(rt.request('accessible','r1')['status'],'queued')
        self.assertEqual(rt.request('pedestrian','r2')['status'],'rejected')
        rt.exchange();self.assertEqual(sent[-1]['requests'],[False]*3)
        now[0]=1.1;self.assertFalse(rt.snapshot()['connected'])
        self.assertEqual(rt.request('pedestrian','r3')['status'],'rejected')

    def test_error_retains_level_and_late_reply_invalidates(self):
        now=[0.0]
        rt=RTService(lambda m,p:json.dumps(state(json.loads(p)['frame'])),lambda:now[0]);rt.exchange()
        rt.request('pedestrian','r')
        def fail(m,p): raise RuntimeError('timeout')
        rt.call=fail;rt.exchange();self.assertTrue(rt.requests[0]);self.assertFalse(rt.snapshot()['connected'])
        def late(m,p):
            now[0]+=.251
            return json.dumps(state(json.loads(p)['frame']))
        rt.call=late;rt.exchange();self.assertFalse(rt.snapshot()['connected']);self.assertTrue(rt.requests[0])

    def test_latest_and_stream_reset(self):
        rt=RTService();rt.publish(frame())
        with self.assertRaises(ValueError): rt.publish(frame())
        rt.publish(frame()|{'frame':2,'time_ms':101})
        rt.requests=[True]*3
        rt.publish(frame()|{'stream':8})
        self.assertEqual(rt.requests,[False]*3)


if __name__=='__main__': unittest.main()
