#!/bin/sh
[ "${DEVICE_ID:-0}" = 285 ] || exit 0
if /mnt/SDCARD/App/VividColors/colors.sh restore > /tmp/mini_flip_colors.log 2>&1; then
    /mnt/SDCARD/.tmp_update/bin/infoPanel --title "Restore handheld colors" --message "Color settings updated.\nLaunch a game to see the change."
else
    /mnt/SDCARD/.tmp_update/bin/infoPanel --title "Color settings" --message "Some settings could not be changed.\nSee /tmp/mini_flip_colors.log."
fi
