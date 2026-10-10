#!/bin/sh
# One-time reset of CFG overrides and selected visual-core OPT files, with rollback.
set -eu
sd=${MINIFLIP_SD:-/mnt/SDCARD}
[ "${DEVICE_ID:-0}" = 285 ] || exit 0
profile="$sd/Saves/CurrentProfile"
[ -d "$profile/config" ] || exit 0
assets="$sd/.tmp_update/res/display"
state="$profile/.mini-flip-display-v3"
action=${1:-boot}
case "$action" in boot|balanced|clean|restore) ;; *) exit 2 ;; esac
res=640x480
[ ! -f /tmp/new_res_available ] || res=752x560
res=${MINIFLIP_RES:-$res}
case "$res" in 640x480|752x560) ;; *) exit 2 ;; esac
mkdir -p "$state"
lock=${MINIFLIP_LOCK:-/tmp/mini_flip_display.lock}
if ! mkdir "$lock" 2>/dev/null; then
    owner=$(cat "$lock/pid" 2>/dev/null || true)
    case "$owner" in ''|*[!0-9]*) exit 1 ;; esac
    if kill -0 "$owner" 2>/dev/null; then exit 1; fi
    rm -f "$lock/pid"
    rmdir "$lock" || exit 1
    mkdir "$lock" || exit 1
fi
echo $$ > "$lock/pid"
trap 'rm -f "$lock/pid"; rmdir "$lock"' EXIT
trap 'exit 1' HUP INT TERM
cycle=$(cat "$state/active" 2>/dev/null || echo 0)
case "$cycle" in ''|*[!0-9]*) exit 1 ;; esac
session="$state/snapshot-$cycle"
if [ "$action" = restore ]; then
    touch "$state/disabled"
    conflicts=0
    if [ -f "$session/files" ]; then
        while IFS= read -r rel; do
            dst="$profile/config/$rel"
            if [ ! -f "$dst" ]; then
                :
            elif [ -f "$session/applied/$rel" ] && cmp -s "$dst" "$session/applied/$rel"; then
                rm -f "$dst"
            elif [ -f "$session/archive/$rel" ] && cmp -s "$dst" "$session/archive/$rel"; then
                :
            else
                echo "Kept modified configuration: $rel"
                conflicts=1
            fi
        done < "$session/files"
    fi
    if [ -f "$session/reset-files" ]; then
        while IFS= read -r rel; do
            old="$session/archive/$rel"
            dst="$profile/config/$rel"
            [ -f "$old" ] || continue
            if [ ! -e "$dst" ]; then
                mkdir -p "$(dirname "$dst")"
                cp "$old" "$dst.display-tmp"
                mv "$dst.display-tmp" "$dst"
            elif ! cmp -s "$old" "$dst"; then
                echo "Kept modified configuration: $rel"
                conflicts=1
            fi
        done < "$session/reset-files"
    fi
    touch "$session/restored"
    sync
    exit "$conflicts"
fi
mode=$action
if [ "$action" = boot ]; then
    [ ! -f "$state/disabled" ] || exit 0
    mode=$(cat "$state/mode" 2>/dev/null || echo balanced)
    case "$mode" in balanced|clean) ;; *) mode=balanced ;; esac
    [ "$(cat "$session/complete" 2>/dev/null || true)" != "$res/$mode" ] || exit 0
fi
src="$assets/profiles/$res/$mode"
[ -d "$src" ] && [ -d "$assets/baseline" ] || exit 1
for cfg in "$assets/overlays/$res/"*.cfg; do
    [ -s "$cfg" ] && [ -s "${cfg%.cfg}.png" ] || exit 1
done
if [ "$res/$mode" = 752x560/balanced ]; then
    for kind in gb gbc gba; do
        [ -s "$assets/ozboss/$kind/$kind.cfg" ] && [ -s "$assets/ozboss/$kind/$kind.png" ] || exit 1
    done
    filters="$sd/RetroArch/.retroarch/filters/video/Offset_Custom"
    [ -s "$filters/Offset_up10px.filt" ] && [ -s "$filters/offset_up.so" ] || exit 1
fi
# A new snapshot is needed only initially or after an explicit restore.
# Existing snapshots are retained, never overwritten.
if [ "$cycle" = 0 ] || [ -f "$session/restored" ]; then
    cycle=$((cycle + 1))
    session="$state/snapshot-$cycle"
    mkdir -p "$session"
    echo "$cycle" > "$state/active.tmp"
    mv "$state/active.tmp" "$state/active"
fi
if [ ! -f "$session/reset-complete" ]; then
    if [ ! -f "$session/reset-files" ]; then
        (cd "$profile/config" && find . -type f \( -name '*.cfg' -o \( -name '*.opt' \( -path './Gambatte/*' -o -path './gpSP/*' -o -path './mGBA/*' \) \) \) | sed 's|^./||' | sort) > "$session/reset-files.tmp"
        mv "$session/reset-files.tmp" "$session/reset-files"
    fi
    while IFS= read -r rel; do
        dst="$profile/config/$rel"
        old="$session/archive/$rel"
        if [ -f "$dst" ]; then
            [ ! -e "$old" ] || exit 1
            mkdir -p "$(dirname "$old")"
            # Same-filesystem atomic rename: no deletion before backup.
            mv "$dst" "$old"
        else
            [ -f "$old" ] || exit 1
        fi
    done < "$session/reset-files"
    touch "$session/reset-complete"
fi
# Seed known Onion defaults (including required core audio settings), then
# apply our display keys. Never copy the user's old overrides back here.
{
    (cd "$assets/baseline" && find . -type f -name '*.cfg')
    (cd "$src" && find . -type f \( -name '*.cfg' -o -name '*.opt' \))
} | sed 's|^./||' | sort -u > "$session/files.tmp"
mv "$session/files.tmp" "$session/files"
while IFS= read -r rel; do
    dst="$profile/config/$rel"
    if [ "$action" = boot ] && [ -f "$session/complete" ] && [ -f "$session/applied/$rel" ]; then
        if [ ! -f "$dst" ] || ! cmp -s "$dst" "$session/applied/$rel"; then
            echo "Kept modified configuration: $rel"
            continue
        fi
    fi
    mkdir -p "$(dirname "$dst")" "$(dirname "$session/applied/$rel")"
    if [ ! -f "$dst" ]; then
        if [ -f "$assets/baseline/$rel" ]; then
            cp "$assets/baseline/$rel" "$dst.display-tmp"
        else
            : > "$dst.display-tmp"
        fi
        mv "$dst.display-tmp" "$dst"
    fi
    if [ -f "$src/$rel" ]; then
        awk 'FNR==NR { key=$0; sub(/=.*/,"",key); gsub(/[ \t\r]/,"",key); keys[key]=1; next }
             { key=$0; sub(/=.*/,"",key); gsub(/[ \t\r]/,"",key); if (!(key in keys)) print }' "$src/$rel" "$dst" > "$dst.display-tmp"
        cat "$src/$rel" >> "$dst.display-tmp"
        mv "$dst.display-tmp" "$dst"
    fi
    cp "$dst" "$session/applied/$rel.tmp"
    mv "$session/applied/$rel.tmp" "$session/applied/$rel"
done < "$session/files"
echo "$mode" > "$state/mode.tmp"
mv "$state/mode.tmp" "$state/mode"
echo "$res/$mode" > "$session/complete.tmp"
mv "$session/complete.tmp" "$session/complete"
rm -f "$state/disabled"
sync
echo "Applied Mini Flip $mode defaults ($res); old overrides archived in $session/archive."
