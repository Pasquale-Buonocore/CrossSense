"""Linux owns the sequence; STM32 applies each LED command via Bridge RPC."""
import time

from arduino.app_utils import App, Bridge

STEP_SECONDS = 0.5
RETRY_SECONDS = 1.0
COLORS = {0: "spento", 1: "rosso", 2: "verde", 3: "blu"}

# (LED number, color): edit this list to change the sequence from Linux.
# Add (0, 0) for a step with all LEDs off.
SEQUENCE = [
    (3, 1),
    (4, 1),
    (3, 2),
    (4, 2),
    (3, 3),
    (4, 3),
]
step_index = 0


def loop():
    global step_index
    led, color = SEQUENCE[step_index]
    expected_ack = led * 10 + color
    started = time.monotonic()
    try:
        ack = Bridge.call("crosssense_set_led", led, color)
        if type(ack) is not int or ack != expected_ack:
            raise RuntimeError(f"Risposta STM32 inattesa: {ack!r}; attesa: {expected_ack}")
        mcu_changes = Bridge.call("crosssense_get_led_change_count")
        if type(mcu_changes) is not int or mcu_changes < 0:
            raise RuntimeError(f"Contatore STM32 non valido: {mcu_changes!r}")
        elapsed_ms = (time.monotonic() - started) * 1000
        print(
            f"LED_OK step={step_index + 1} led={led} color={COLORS[color]} "
            f"ack={ack} mcu_changes={mcu_changes} roundtrip_ms={elapsed_ms:.2f}",
            flush=True,
        )
    except Exception as error:
        print(f"LED_ERROR {type(error).__name__}: {error}; riprovo lo stesso passo", flush=True)
        time.sleep(RETRY_SECONDS)
        return

    step_index = (step_index + 1) % len(SEQUENCE)
    time.sleep(STEP_SECONDS)


print("CrossSense Linux LED Counter: comandi Linux -> STM32, contatore STM32 -> Linux", flush=True)
App.run(user_loop=loop)
