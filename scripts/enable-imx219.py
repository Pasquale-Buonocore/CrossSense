"""Select the installed UNO Q IMX219 device tree; default is preview only."""
import argparse
import difflib
import os
from pathlib import Path
import platform
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--reboot", action="store_true")
    args = parser.parse_args()
    if args.reboot and not args.apply:
        parser.error("--reboot richiede --apply")
    dtb = Path("/boot/efi/dtb/qcom/qrb2210-arduino-imola-camera-rpiv2.dtb")
    if not dtb.is_file():
        raise SystemExit("DTB IMX219 non trovato; nessuna modifica.")
    machine = Path("/etc/machine-id").read_text().strip()
    entries = list(Path("/boot/efi/loader/entries").glob(
        f"{machine}-{platform.release()}.conf"))
    if len(entries) != 1:
        raise SystemExit("Entry del kernel corrente non univoca; nessuna modifica.")
    entry = entries[0]
    original = entry.read_text()
    directive = "devicetree /dtb/qcom/qrb2210-arduino-imola-camera-rpiv2.dtb\n"
    lines = original.splitlines(keepends=True)
    revised = "".join(line for line in lines if not line.lstrip().startswith("devicetree "))
    revised = revised.rstrip("\n") + "\n" + directive
    print(f"Boot entry: {entry}")
    if revised == original:
        print("Configurazione IMX219 già selezionata.")
    else:
        print("".join(difflib.unified_diff(original.splitlines(True),
                                        revised.splitlines(True),
                                        fromfile="attuale", tofile="IMX219")))
        if not args.apply:
            print("Anteprima: nessun file modificato. Servono --apply e privilegi root.")
            return
        if os.geteuid() != 0:
            raise SystemExit("Eseguire con sudo; nessuna modifica.")
        backup_dir = Path("/boot/efi/crosssense-backups")
        backup_dir.mkdir(exist_ok=True)
        backup = backup_dir / f"{entry.name}.{time.time_ns()}.bak"
        with backup.open("x") as output:
            output.write(original)
            output.flush()
            os.fsync(output.fileno())
        temporary = entry.with_suffix(".conf.crosssense-tmp")
        with temporary.open("x") as output:
            output.write(revised)
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(entry)
        os.sync()
        print(f"Backup: {backup}")
        print(f"Ripristino: sudo cp {backup} {entry}")
        print("Configurazione applicata; diventa attiva al prossimo boot.")
    if args.reboot:
        if os.geteuid() != 0:
            raise SystemExit("Riavvio richiede sudo.")
        subprocess.run(["/usr/sbin/reboot"], check=True)


if __name__ == "__main__":
    main()
