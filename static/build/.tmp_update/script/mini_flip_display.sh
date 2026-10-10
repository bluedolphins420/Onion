#!/bin/sh
# One-time display migration. Only managed display keys are replaced.
set -eu
sd=${MINIFLIP_SD:-/mnt/SDCARD}
[ "${DEVICE_ID:-0}" = 285 ] || exit 0
profile="$sd/Saves/CurrentProfile"
[ -d "$profile/config" ] || exit 0
assets="$sd/.tmp_update/res/display"
state="$profile/.mini-flip-display-v1"
action=${1:-boot}
case "$action" in boot|balanced|clean|restore) ;; *) exit 2 ;; esac
res=640x480
[ ! -f /tmp/new_res_available ] || res=752x560
res=${MINIFLIP_RES:-$res}
case "$res" in 640x480|752x560) ;; *) exit 2 ;; esac
mkdir -p "$state"
# A stale lock is removable after restart; never steal a live migration.
if ! mkdir "$state/lock" 2>/dev/null; then
    owner=$(cat "$state/lock/pid" 2>/dev/null || true)
    case "$owner" in ''|*[!0-9]*) exit 1 ;; esac
    if kill -0 "$owner" 2>/dev/null; then exit 1; fi
    rm -f "$state/lock/pid"
    rmdir "$state/lock" || exit 1
    mkdir "$state/lock" || exit 1
fi
echo $$ > "$state/lock/pid"
trap 'rm -f "$state/lock/pid"; rmdir "$state/lock"' EXIT
trap 'exit 1' HUP INT TERM
if [ "$action" = restore ]; then
    touch "$state/disabled"
    conflicts=0
    if [ -f "$state/files" ]; then
        while IFS= read -r rel; do
            dst="$profile/config/$rel"
            if [ -f "$state/applied/$rel" ] && [ -f "$dst" ] && cmp -s "$dst" "$state/applied/$rel"; then
                keys="$assets/profiles/752x560/balanced/$rel"
                # Restore only managed display keys. Preserve unrelated settings
                # even when they were edited before a later profile switch.
                awk 'FNR==NR { key=$0; sub(/=.*/,"",key); gsub(/[ \t\r]/,"",key); keys[key]=1; next }
                     { key=$0; sub(/=.*/,"",key); gsub(/[ \t\r]/,"",key); if (!(key in keys)) print }' "$keys" "$dst" > "$dst.display-tmp"
                if [ -f "$state/original/$rel" ]; then
                    awk 'FNR==NR { key=$0; sub(/=.*/,"",key); gsub(/[ \t\r]/,"",key); keys[key]=1; next }
                         { key=$0; sub(/=.*/,"",key); gsub(/[ \t\r]/,"",key); if (key in keys) print }' "$keys" "$state/original/$rel" >> "$dst.display-tmp"
                fi
                if [ -s "$dst.display-tmp" ] || [ -f "$state/original/$rel" ]; then
                    mv "$dst.display-tmp" "$dst"
                else
                    rm -f "$dst.display-tmp" "$dst"
                fi
                # Record the restored file so repeated restore is idempotent.
                if [ -f "$dst" ]; then cp "$dst" "$state/applied/$rel"; fi
            elif [ -f "$state/original/$rel" ] && [ -f "$dst" ] && cmp -s "$dst" "$state/original/$rel"; then
                : # already restored
            elif [ ! -f "$dst" ] && [ -f "$state/missing/$rel" ]; then
                :
            else
                echo "Kept modified configuration: $rel"
                conflicts=1
            fi
        done < "$state/files"
    fi
    sync
    exit "$conflicts"
fi
mode=$action
if [ "$action" = boot ]; then
    [ ! -f "$state/disabled" ] || exit 0
    mode=$(cat "$state/mode" 2>/dev/null || echo balanced)
    case "$mode" in balanced|clean) ;; *) mode=balanced ;; esac
    [ "$(cat "$state/complete" 2>/dev/null || true)" != "$res/$mode" ] || exit 0
fi
src="$assets/profiles/$res/$mode"
[ -d "$src" ] || exit 1
# Validate referenced images before touching any configs.
for cfg in "$assets/overlays/$res/"*.cfg; do
    [ -s "$cfg" ] && [ -s "${cfg%.cfg}.png" ] || exit 1
done
(cd "$src" && find . -type f -name '*.cfg' | sed 's|^./||' | sort) > "$state/files.tmp"
[ -s "$state/files.tmp" ] || exit 1
mv "$state/files.tmp" "$state/files"
while IFS= read -r rel; do
    dst="$profile/config/$rel"
    # Resolution changes may refresh untouched profiles, never custom edits.
    if [ "$action" = boot ] && [ -f "$state/complete" ] && [ -f "$state/applied/$rel" ]; then
        if [ ! -f "$dst" ] || ! cmp -s "$dst" "$state/applied/$rel"; then
            echo "Kept modified configuration: $rel"
            continue
        fi
    fi
    mkdir -p "$(dirname "$dst")" "$(dirname "$state/original/$rel")" "$(dirname "$state/missing/$rel")" "$(dirname "$state/applied/$rel")"
    if [ ! -f "$state/original/$rel" ] && [ ! -f "$state/missing/$rel" ]; then
        if [ -f "$dst" ]; then
            cp "$dst" "$state/original/$rel.tmp"
            mv "$state/original/$rel.tmp" "$state/original/$rel"
        else
            touch "$state/missing/$rel"
        fi
    fi
    input=$dst
    [ -f "$input" ] || input=/dev/null
    awk 'FNR==NR { key=$0; sub(/=.*/,"",key); gsub(/[ \t\r]/,"",key); keys[key]=1; next }
         { key=$0; sub(/=.*/,"",key); gsub(/[ \t\r]/,"",key); if (!(key in keys)) print }' "$src/$rel" "$input" > "$dst.display-tmp"
    cat "$src/$rel" >> "$dst.display-tmp"
    mv "$dst.display-tmp" "$dst"
    cp "$dst" "$state/applied/$rel.tmp"
    mv "$state/applied/$rel.tmp" "$state/applied/$rel"
done < "$state/files"
echo "$mode" > "$state/mode.tmp"
mv "$state/mode.tmp" "$state/mode"
echo "$res/$mode" > "$state/complete.tmp"
mv "$state/complete.tmp" "$state/complete"
rm -f "$state/disabled"
sync
echo "Applied Mini Flip $mode display defaults ($res)."
