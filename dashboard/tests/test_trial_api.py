from functools import partial
from http.client import HTTPConnection
import json
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from urllib.error import HTTPError
from urllib.request import Request,urlopen

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Handler, DashboardServer
from rt import RTService
from layout import LayoutStore


class QuietHandler(Handler):
    def log_message(self,*args): pass


class TrialAPITests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        static=Path(__file__).resolve().parents[1]/'static'
        self.server=DashboardServer(('127.0.0.1',0),partial(QuietHandler,directory=str(static)))
        self.server.rt=RTService()
        self.server.layout=LayoutStore(Path(self.folder.name)/'layout.json')
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown();self.thread.join(timeout=2)
        self.server.server_close();self.folder.cleanup()

    def call(self,path,data=None):
        request=Request(self.url+path,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json'})
        try:
            with urlopen(request,timeout=2) as response:
                return response.status,json.load(response)
        except HTTPError as exc:
            return exc.code,json.load(exc)

    def test_replay_is_default_with_or_without_bridge(self):
        self.assertEqual(self.call('/api/config')[1]['default_mode'],'replay')
        self.server.rt.call=lambda *args:None
        self.assertEqual(self.call('/api/config')[1]['default_mode'],'replay')

    def test_polling_and_static_content_reuse_one_connection(self):
        connection=HTTPConnection('127.0.0.1',self.server.server_port,timeout=2)
        try:
            connection.connect();sock=connection.sock
            for path in ('/api/config','/api/rt','/vision.js','/api/vision/frame.jpg?serial=999','/api/config'):
                connection.request('GET',path)
                response=connection.getresponse();response.read()
                self.assertEqual(response.version,11)
                self.assertFalse(response.will_close)
                self.assertIs(connection.sock,sock)
        finally:connection.close()

    def test_rejected_unread_post_body_closes_connection(self):
        connection=HTTPConnection('127.0.0.1',self.server.server_port,timeout=2)
        try:
            connection.request('POST','/api/requests',body='{}',headers={'Content-Type':'text/plain'})
            response=connection.getresponse();response.read()
            self.assertEqual(response.status,415)
            self.assertTrue(response.will_close)
        finally:connection.close()

    def test_trial_unavailable_and_one_run_at_a_time(self):
        self.assertFalse(self.call('/api/trial')[1]['available'])
        self.assertEqual(self.call('/api/trial',{})[0],409)
        self.server.trial=SimpleNamespace(snapshot=lambda:{'available':True,'status':'completed'},start=lambda:{'status':'started'})
        self.assertEqual(self.call('/api/trial',{})[1]['status'],'started')
        self.server.trial.start=lambda:{'status':'rejected','reason':'Prova già in corso'}
        self.assertEqual(self.call('/api/trial',{})[0],409)
        self.assertEqual(self.call('/api/trial',{'phase':'PED_GREEN'})[0],400)

    def test_static_and_api_responses_are_not_cached(self):
        for path in ('/api/config','/app.js','/'):
            with urlopen(self.url+path,timeout=2) as response:
                self.assertEqual(response.headers['Cache-Control'],'no-store')


if __name__=='__main__':unittest.main()
