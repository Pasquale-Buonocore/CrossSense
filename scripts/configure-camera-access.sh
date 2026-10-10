#!/bin/sh
# Allow the existing video group to use only the system DMA heap.
set -eu
[ "$(id -u)" -eq 0 ] || { echo 'Eseguire con sudo'; exit 1; }
rule=/etc/udev/rules.d/99-crosssense-camera-dma.rules
if [ -e "$rule" ]; then
    cp -p "$rule" "$rule.backup-$(date +%s)"
fi
printf '%s\n' 'SUBSYSTEM=="dma_heap", KERNEL=="system", GROUP="video", MODE="0660"' > "$rule"
udevadm control --reload-rules
udevadm trigger --action=change --subsystem-match=dma_heap
udevadm settle
ls -l /dev/dma_heap/system
