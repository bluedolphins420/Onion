#!/bin/sh
sysdir=/mnt/SDCARD/.tmp_update
[ "$DEVICE_ID" = "285" ] || exit 1
[ -x "$sysdir/bin/MainUI-open" ] || exit 1
mkdir -p "$sysdir/config" || exit 1
: > "$sysdir/config/.openMainUI" || exit 1
sync
