"""Diagnostica CrossSense; nessuna inferenza o uscita luminosa implementata."""

import argparse
from pathlib import Path
import time

from crosssense.config import APP_ROOT, load_config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Controllo locale senza Arduino")
    parser.add_argument(
        "--config", type=Path, default=APP_ROOT / "config" / "crossing.example.json"
    )
    args = parser.parse_args()
    config = load_config(args.config)
    print("CrossSense: scaffold pronto, uscite disabilitate.", flush=True)
    if args.check:
        print("Configurazione valida. Camera, AI e controllo semaforico da implementare.")
        return

    # Import locale: il controllo sul PC non richiede il runtime della scheda.
    from arduino.app_utils import App, Bridge

    def loop() -> None:
        status = Bridge.call("crosssense_status")
        if status != "scaffold_ready":
            raise RuntimeError(f"Risposta MCU inattesa: {status!r}")
        print(f"MCU: {status}", flush=True)
        time.sleep(config["diagnostic_interval_s"])

    App.run(user_loop=loop)


if __name__ == "__main__":
    main()
