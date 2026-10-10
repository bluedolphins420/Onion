#!/bin/sh
[ "${DEVICE_ID:-0}" = 285 ] || exit 0
sd=/mnt/SDCARD
log="$sd/App/AllOverlays/last-run.log"
if sh "$sd/App/AllOverlays/apply.sh" apply > "$log" 2>&1; then
    "$sd/.tmp_update/bin/infoPanel" --title "Overlay settings" --message "Settings updated.\nLaunch a game to see the change."
else
    "$sd/.tmp_update/bin/infoPanel" --title "Overlay setup failed" --message "Report saved on your SD card:\nApp/AllOverlays/last-run.log\nSend that file for the exact cause."
fi
cp "$log" /tmp/mini_flip_all_overlays.log
