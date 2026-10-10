"""Small ADB wrapper for the UNO Q; never chooses among multiple devices."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys


def find_adb():
    executable = shutil.which("adb")
    if executable:
        return executable
    root = Path.home() / "Library/Arduino15/packages/arduino/tools/adb"
    candidates = sorted(root.glob("*/adb"))
    if candidates:
        return str(candidates[-1])
    raise SystemExit("ADB non trovato: installare gli strumenti Arduino/ADB.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", help="Seriale ADB della UNO Q")
    parser.add_argument("action", choices=["devices", "shell", "push", "pull"])
    parser.add_argument("arguments", nargs="*")
    args = parser.parse_args()
    adb = find_adb()
    if args.action == "devices":
        return subprocess.call([adb, "devices", "-l"])
    devices = subprocess.check_output([adb, "devices"], text=True)
    available = [line.split()[0] for line in devices.splitlines()[1:]
                 if len(line.split()) == 2 and line.split()[1] == "device"]
    serial = args.serial
    if serial is None:
        if len(available) != 1:
            parser.error("Serve una sola scheda collegata oppure --serial SERIAL")
        serial = available[0]
    if serial not in available:
        parser.error("Scheda assente o non autorizzata")
    if args.action in ("push", "pull") and len(args.arguments) != 2:
        parser.error("push/pull richiedono sorgente e destinazione")
    return subprocess.call([adb, "-s", serial, args.action, *args.arguments])


if __name__ == "__main__":
    sys.exit(main())
