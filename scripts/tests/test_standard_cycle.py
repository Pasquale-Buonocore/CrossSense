import importlib.util
import socket
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import URLError

script = Path(__file__).resolve().parents[1]/'try_standard_cycle.py'
spec = importlib.util.spec_from_file_location('try_standard_cycle', script)
cycle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cycle)


def snapshot(phase, **changes):
    vehicle, pedestrian = cycle.LIGHTS[phase]
    state = dict(phase=phase, vehicle_light=vehicle, pedestrian_light=pedestrian,
                 observation_valid=True, fault=None, alarms=[], ok=True,
                 remaining_ms=None)
    state.update(changes)
    return dict(connected=True, state=state, error=None)


class FakeClient:
    def __init__(self, states):
        self.states = iter(states)
        self.last = None
        self.samples = []
        self.requests = []

    def observe(self, valid=True):
        self.samples.append(valid)

    def snapshot(self):
        self.last = next(self.states, self.last)
        return self.last

    def request(self, request_id):
        self.requests.append(request_id)
        return {'status': 'rejected' if len(self.requests) == 1 else 'queued'}


class CycleDriverTests(unittest.TestCase):
    def run_driver(self, client, cycles=1, timeout=10):
        now = [0.0]
        def sleep(duration): now[0] += max(0.01, duration)
        cycle.run_cycle(client, cycles, timeout, clock=lambda: now[0], sleep=sleep,
                        emit=lambda *args, **kwargs: None)

    def test_two_cycles_request_retry_and_new_ids(self):
        client = FakeClient([snapshot('FAULT'), snapshot('ALL_RED_TO_VEH')]+
                            [snapshot(p) for p in ('VEHICLE_GREEN',)+cycle.PHASES+cycle.PHASES])
        self.run_driver(client, cycles=2)
        self.assertEqual(client.requests[0], client.requests[1])
        self.assertNotEqual(client.requests[1], client.requests[-1])

    def test_skipped_phase_and_conflicting_outputs_fail(self):
        for bad in (snapshot('PED_GREEN'), snapshot('VEHICLE_GREEN', pedestrian_light='GREEN')):
            with self.assertRaises(RuntimeError):
                self.run_driver(FakeClient([snapshot('VEHICLE_GREEN'), bad]))

    def test_transition_without_queued_request_fails(self):
        with self.assertRaisesRegex(RuntimeError, 'senza conferma'):
            self.run_driver(FakeClient([snapshot('VEHICLE_GREEN'), snapshot('VEHICLE_YELLOW')]))

    def test_fault_mid_cycle_fails(self):
        client = FakeClient([snapshot('VEHICLE_GREEN'), snapshot('FAULT', observation_valid=False, fault='TIMEOUT')])
        with self.assertRaisesRegex(RuntimeError, 'guasto/allarme'):
            self.run_driver(client)

    def test_disconnected_and_protected_firmware_diagnostics(self):
        for state, expected in (({'connected': False, 'error': 'no bridge'}, 'non disponibile'),
                                (snapshot('PROTECTED_STOP'), 'modalità protetta')):
            with self.assertRaisesRegex(RuntimeError, expected):
                self.run_driver(FakeClient([state]))

    def test_watchdog_requires_red_outputs_and_fault(self):
        now = [0.0]
        def sleep(duration): now[0] += duration
        client = FakeClient([snapshot('VEHICLE_GREEN'), snapshot('FAULT', observation_valid=False, fault='INVALID_DATA')])
        cycle.check_watchdog(client, clock=lambda: now[0], sleep=sleep, emit=lambda *args, **kwargs: None)
        client = FakeClient([snapshot('FAULT', observation_valid=False, fault='TIMEOUT', vehicle_light='GREEN')])
        with self.assertRaisesRegex(RuntimeError, 'Uscite incoerenti'):
            cycle.check_watchdog(client)

    def test_frame_format_order_and_shutdown(self):
        client = cycle.APIClient('http://test:8081/')
        sent = []
        client.call = lambda path, frame: sent.append((path, frame)) or {'status': 'buffered'}
        with patch.object(cycle.time, 'monotonic_ns', return_value=1_000_000):
            client.observe();client.observe();client.observe(False)
        self.assertEqual([f['frame'] for _, f in sent], [1, 2, 3])
        self.assertEqual([f['time_ms'] for _, f in sent], [1, 2, None])
        self.assertEqual(sent[-1][1]['requests'], [False]*3)
        self.assertEqual(sent[-1][1]['crossing'], 'unknown')

    def test_dns_failure_explains_placeholder(self):
        client = cycle.APIClient('http://IP-DELLA-UNO-Q:8081')
        with patch.object(cycle, 'urlopen', side_effect=URLError(socket.gaierror(11001, 'getaddrinfo failed'))):
            with self.assertRaisesRegex(RuntimeError, 'segnaposto'):
                client.snapshot()


if __name__ == '__main__':
    unittest.main()
