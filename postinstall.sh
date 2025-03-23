#!/bin/sh

systemd=$(command -v deb-systemd-invoke || echo "systemctl")

"$systemd" --system daemon-reload >/dev/null || true
if ! "$systemd" is-enabled frr-evpn-route-watcher.timer >/dev/null
then
    "$systemd" enable frr-evpn-route-watcher.timer >/dev/null || true
    "$systemd" start frr-evpn-route-watcher.timer >/dev/null || true
else
    "$systemd" restart frr-evpn-route-watcher.timer >/dev/null || true
fi
