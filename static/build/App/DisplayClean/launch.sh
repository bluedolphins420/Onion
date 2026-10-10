#!/bin/sh
if [ "${DEVICE_ID:-0}" != 285 ]; then exit 0; fi
if /mnt/SDCARD/.tmp_update/script/mini_flip_display.sh clean > /tmp/mini_flip_display.log 2>&1; then
    /mnt/SDCARD/.tmp_update/bin/infoPanel --title "Clean display" --message "Display settings updated.\nChanges apply when you next launch a game."
else
    /mnt/SDCARD/.tmp_update/bin/infoPanel --title "Display settings" --message "Some settings were kept or could not be updated.\nSee /tmp/mini_flip_display.log.\nYour backup remains in Saves/CurrentProfile/.mini-flip-display-v3."
fi
