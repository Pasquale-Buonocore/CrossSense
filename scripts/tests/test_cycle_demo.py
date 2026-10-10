import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root/'scripts'))
sys.path.insert(0, str(root/'dashboard'))
spec = importlib.util.spec_from_file_location('cycle_demo', root/'firmware'/'python'/'cycle_demo.py')
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


class AutomaticDemoTests(unittest.TestCase):
    def test_local_url_cycles_and_cleanup(self):
        client = Mock()
        with patch.object(demo, 'APIClient', return_value=client) as factory, \
             patch.object(demo, 'run_cycle') as run, \
             patch.object(demo, 'check_watchdog') as watchdog, \
             contextlib.redirect_stdout(io.StringIO()):
            thread, result = demo.start_demo(SimpleNamespace(server_port=8091))
            thread.join(timeout=1)
        self.assertFalse(thread.is_alive())
        self.assertTrue(result['ok'])
        factory.assert_called_once_with('http://127.0.0.1:8091')
        run.assert_called_once_with(client, cycles=2, timeout=80)
        watchdog.assert_called_once_with(client)
        client.observe.assert_called_once_with(valid=False)

    def test_failure_is_reported_and_invalid_frame_published(self):
        client = Mock()
        with patch.object(demo, 'APIClient', return_value=client), \
             patch.object(demo, 'run_cycle', side_effect=RuntimeError('Bridge down')), \
             contextlib.redirect_stdout(io.StringIO()):
            thread, result = demo.start_demo(SimpleNamespace(server_port=8081))
            thread.join(timeout=1)
        self.assertFalse(result['ok'])
        self.assertEqual(result['error'], 'Bridge down')
        client.observe.assert_called_once_with(valid=False)

    def test_duplicate_start_rejected_and_completed_trial_can_repeat(self):
        client=Mock();entered=threading.Event();release=threading.Event()
        def run(*args,**kwargs):
            entered.set();release.wait(timeout=2)
        with patch.object(demo,'APIClient',return_value=client), \
             patch.object(demo,'run_cycle',side_effect=run), \
             patch.object(demo,'check_watchdog'), \
             contextlib.redirect_stdout(io.StringIO()):
            server=SimpleNamespace(server_port=8081)
            thread,result=demo.start_demo(server)
            self.assertTrue(entered.wait(timeout=1))
            self.assertEqual(server.trial.snapshot()['status'],'running')
            self.assertEqual(server.trial.start()['status'],'rejected')
            release.set();thread.join(timeout=1)
            self.assertEqual(server.trial.snapshot()['status'],'completed')
            self.assertEqual(server.trial.start()['status'],'started')
            server.trial.thread.join(timeout=1)
            self.assertTrue(server.trial.result['ok'])

    def test_callback_does_not_run_when_port_binding_fails(self):
        import server
        ready = Mock()
        with patch.object(sys, 'argv', ['server.py']), \
             patch.object(server, 'ThreadingHTTPServer', side_effect=OSError('port occupied')):
            with self.assertRaises(OSError):
                server.main(on_ready=ready)
        ready.assert_not_called()


if __name__ == '__main__':
    unittest.main()
