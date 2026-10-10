from pathlib import Path
import sys
import tempfile
import unittest
import os
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from native import NativeController, BridgeController


class TransportTests(unittest.TestCase):
    def test_bridge_worker_handshake_and_sdk_log_isolation(self):
        with tempfile.TemporaryDirectory() as folder:
            package=Path(folder)/'arduino';package.mkdir()
            (package/'__init__.py').write_text('')
            (package/'app_utils.py').write_text(
                'print("SDK startup log")\n'
                'class Bridge:\n'
                ' @staticmethod\n'
                ' def call(method,payload):\n'
                '  print("SDK call log")\n'
                '  return method+":"+payload\n')
            transport=BridgeController()
            transport.timeout=2
            try:
                with patch.dict(os.environ,{'PYTHONPATH':folder}):
                    self.assertEqual(transport('crosssense_update','{}'),'crosssense_update:{}')
                    self.assertEqual(transport('crosssense_update','next'),'crosssense_update:next')
            finally:transport.close()

    def test_blocked_process_is_terminated_and_can_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            script=Path(folder)/'worker.py'
            script.write_text('import sys,time\nfor line in sys.stdin: time.sleep(5)\n')
            transport=NativeController(sys.executable,timeout=.05)
            transport.command=[sys.executable,'-u',str(script)]
            try:
                with self.assertRaisesRegex(RuntimeError,'timeout'):transport('crosssense_update','{}')
                self.assertIsNone(transport.process)
                self.assertEqual(transport.resets,1)
                script.write_text('import sys\nfor line in sys.stdin: print("response",flush=True)\n')
                transport.timeout=1
                self.assertEqual(transport('crosssense_update','{}'),'response')
            finally:transport.close()
