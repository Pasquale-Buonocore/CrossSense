#!/bin/sh
# Read-only checks. Run on the UNO Q with: sh /path/to/board-diagnostics.sh
set -u
hostname
cat /etc/os-release
uname -a
free -h
df -h /
ip -brief address
arduino-app-cli version
arduino-cli core list
systemctl is-active arduino-router docker
v4l2-ctl --list-devices
cam --list 2>&1
for node in /sys/firmware/devicetree/base/soc@0/camss*/status; do
    [ -f "$node" ] || continue
    printf 'Camera device tree status: '
    tr -d '\000' < "$node"
    printf '\n'
done
