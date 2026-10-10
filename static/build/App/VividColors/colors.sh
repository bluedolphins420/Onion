#!/bin/sh
# Color-only Community4 add-on. No CFG, artwork, scaling or emulator changes.
set -eu
[ "${DEVICE_ID:-0}" = 285 ] || exit 0
sd=${MINIFLIP_SD:-/mnt/SDCARD}
state="$sd/Saves/CurrentProfile/.mini-flip-colors-v1"
action=${1:-apply}
case "$action" in apply|restore) ;; *) exit 2 ;; esac
[ -d "$sd/Saves/CurrentProfile/config" ] || exit 1
lock=${MINIFLIP_LOCK:-/tmp/mini_flip_display.lock}
mkdir "$lock" 2>/dev/null || exit 1
echo $$ > "$lock/pid"
trap 'rm -f "$lock/pid"; rmdir "$lock"' EXIT
trap 'exit 1' HUP INT TERM
mkdir -p "$state"
cycle=$(cat "$state/active" 2>/dev/null || echo 0)
case "$cycle" in ''|*[!0-9]*) exit 1 ;; esac
session="$state/snapshot-$cycle"
if [ "$action" = restore ]; then
    [ -f "$session/files" ] || exit 0
    conflicts=0
    while IFS= read -r rel; do
        dst="$sd/$rel"
        old="$session/original/$rel"
        [ -f "$old" ] || continue
        if [ -f "$dst" ] && cmp -s "$dst" "$old"; then continue; fi
        if [ -f "$session/applied/$rel" ] && [ -f "$dst" ] && cmp -s "$dst" "$session/applied/$rel"; then
            cp "$old" "$dst.color-tmp"
            mv "$dst.color-tmp" "$dst"
        else
            echo "Kept later edit or missing file: $rel"
            conflicts=1
        fi
    done < "$session/files"
    [ "$conflicts" != 0 ] || touch "$session/restored"
    sync
    exit "$conflicts"
fi
if [ "$cycle" = 0 ] || [ -f "$session/restored" ]; then
    cycle=$((cycle + 1));session="$state/snapshot-$cycle"
    mkdir -p "$session"
    echo "$cycle" > "$state/active.tmp";mv "$state/active.tmp" "$state/active"
fi
# Include per-game options and both resolution/mode templates. Unrelated
# keys are retained, and existing pre-apply backups are never overwritten.
if [ ! -f "$session/files" ]; then
    (cd "$sd" && {
        find Saves/CurrentProfile/config -type f -name '*.opt'
        if [ -d .tmp_update/res/display/profiles ]; then
            find .tmp_update/res/display/profiles -type f -name '*.opt'
        fi
    } | grep -E '/(Gambatte|gpSP|mGBA)/' | sort) > "$session/files.tmp"
    [ -s "$session/files.tmp" ] || exit 1
    mv "$session/files.tmp" "$session/files"
fi
while IFS= read -r rel; do
    dst="$sd/$rel"
    [ -f "$dst" ] || continue
    mkdir -p "$session/original/$(dirname "$rel")" "$session/applied/$(dirname "$rel")"
    if [ ! -f "$session/original/$rel" ]; then
        cp "$dst" "$session/original/$rel.tmp"
        mv "$session/original/$rel.tmp" "$session/original/$rel"
    fi
    case "$rel" in
        */Gambatte/*)
            keys='gambatte_gbc_color_correction gambatte_dark_filter_level gambatte_gb_internal_palette gambatte_gb_palette_essentials'
            values='disabled 0 Essentials Greenscale' ;;
        */gpSP/*) keys='gpsp_color_correction';values='disabled' ;;
        */mGBA/*) keys='mgba_color_correction';values='OFF' ;;
    esac
    awk -v keys="$keys" -v values="$values" '
        BEGIN { n=split(keys,k," "); split(values,v," "); for(i=1;i<=n;i++) selected[k[i]]=1 }
        { key=$0; sub(/=.*/,"",key); gsub(/[ \t\r]/,"",key); if (!(key in selected)) print }
        END { for(i=1;i<=n;i++) printf "%s = \"%s\"\n",k[i],v[i] }
    ' "$dst" > "$dst.color-tmp"
    mv "$dst.color-tmp" "$dst"
    cp "$dst" "$session/applied/$rel.tmp"
    mv "$session/applied/$rel.tmp" "$session/applied/$rel"
done < "$session/files"
sync
echo "Vivid colors applied. Backup: $session/original"
