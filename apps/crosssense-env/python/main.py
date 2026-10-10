"""Bridge smoke test, not the traffic controller or its watchdog."""
from arduino.app_utils import App, Bridge
import time


def loop():
    started = time.monotonic_ns()
    try:
        uptime = Bridge.call("crosssense_ping")
        elapsed_ms = (time.monotonic_ns() - started) / 1_000_000
        print(f"BRIDGE_OK mcu_uptime_ms={uptime} roundtrip_ms={elapsed_ms:.2f}", flush=True)
    except Exception as error:
        print(f"BRIDGE_ERROR {type(error).__name__}: {error}", flush=True)
    time.sleep(1)


App.run(user_loop=loop)
