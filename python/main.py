"""Diagnostica CrossSense; nessuna inferenza o uscita luminosa implementata."""

import argparse
import time


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Controllo locale senza Arduino")
    args = parser.parse_args()
    print("CrossSense: scaffold pronto, uscite disabilitate.", flush=True)
    if args.check:
        print("Avvio Python verificato. Camera, AI e controllo semaforico da implementare.")
        return

    # Il controllo sul PC non richiede il runtime della scheda.
    from arduino.app_utils import App, Bridge

    def loop() -> None:
        status = Bridge.call("crosssense_status")
        if status != "scaffold_ready":
            raise RuntimeError(f"Risposta MCU inattesa: {status!r}")
        print(f"MCU: {status}", flush=True)
        time.sleep(1)

    App.run(user_loop=loop)


if __name__ == "__main__":
    main()
