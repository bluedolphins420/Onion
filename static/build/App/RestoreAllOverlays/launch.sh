#!/bin/sh
[ "${DEVICE_ID:-0}" = 285 ] || exit 0
sd=/mnt/SDCARD
log="$sd/App/AllOverlays/last-run.log"
# Return to Onion's menu directly; do not enter a second SDL application.
sh "$sd/App/AllOverlays/apply.sh" restore > "$log" 2>&1 &
worker=$!
# Bound failures on older firmware so setup cannot trap the user on a black screen.
(
    sleep 60
    if kill -0 "$worker" 2>/dev/null; then
        echo "ERROR: setup timed out; backups retained" >> "$log"
        kill -TERM "$worker" 2>/dev/null
        sleep 2
        kill -KILL "$worker" 2>/dev/null
    fi
) &
guard=$!
wait "$worker"
result=$?
kill "$guard" 2>/dev/null
wait "$guard" 2>/dev/null
cp "$log" /tmp/mini_flip_all_overlays.log
exit "$result"
