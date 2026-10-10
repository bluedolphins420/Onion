#!/bin/sh
[ "${DEVICE_ID:-0}" = 285 ] || exit 0
if /mnt/SDCARD/App/AllOverlays/apply.sh apply > /tmp/mini_flip_all_overlays.log 2>&1; then
    /mnt/SDCARD/.tmp_update/bin/infoPanel --title "All system overlays" --message "Overlay settings updated.\nLaunch a game to see the change."
else
    /mnt/SDCARD/.tmp_update/bin/infoPanel --title "Overlay settings" --message "Some settings could not be updated.\nSee /tmp/mini_flip_all_overlays.log.\nBackups remain in Saves/CurrentProfile/.mini-flip-all-overlays-v1."
fi
