#!/bin/sh
# Overlay-only extension for Community4. Preserve handheld color options.
set -eu
stage=initialization
fail() { echo "ERROR: $*"; exit 1; }
report_exit() {
    result=$?
    if [ "$result" != 0 ]; then echo "FAILED stage=$stage status=$result"; fi
    if [ "${locked:-0}" = 1 ]; then rm -f "$lock/pid"; rmdir "$lock"; fi
    exit "$result"
}
trap report_exit EXIT
[ "${DEVICE_ID:-0}" = 285 ] || exit 0
sd=${MINIFLIP_SD:-/mnt/SDCARD}
app="$sd/App/AllOverlays"
profile="$sd/Saves/CurrentProfile"
state="$profile/.mini-flip-all-overlays-v1"
action=${1:-apply}
case "$action" in apply|restore|boot) ;; *) exit 2 ;; esac
[ -d "$profile/config" ] || fail "Missing Saves/CurrentProfile/config"
if [ "$action" = boot ] && [ ! -f "$state/enabled" ]; then exit 0; fi
res=640x480
[ ! -f /tmp/new_res_available ] || res=752x560
res=${MINIFLIP_RES:-$res}
case "$res" in 752x560|640x480) ;; *) exit 2 ;; esac
lock=${MINIFLIP_LOCK:-/tmp/mini_flip_display.lock}
stage=lock
if ! mkdir "$lock" 2>/dev/null; then
    owner=$(cat "$lock/pid" 2>/dev/null || true)
    case "$owner" in ''|*[!0-9]*) fail "Display lock exists without a valid owner; restart the device" ;; esac
    if kill -0 "$owner" 2>/dev/null; then fail "Display setup is already running; retry shortly"; fi
    rm -f "$lock/pid"
    rmdir "$lock" || fail "Cannot clear old display lock"
    mkdir "$lock" || fail "Cannot acquire display lock"
fi
locked=1
echo $$ > "$lock/pid"
stage=backup_state
trap 'exit 1' HUP INT TERM
mkdir -p "$state"
stage=read_snapshot_number
cycle=0
if [ -f "$state/active" ]; then
    IFS= read -r cycle < "$state/active" || [ -n "$cycle" ] || fail "Empty snapshot number"
fi
case "$cycle" in ''|*[!0-9]*) fail "Invalid snapshot number" ;; *) : ;; esac
session="$state/snapshot-$cycle"
if [ "$action" = restore ]; then
    rm -f "$state/enabled"
    [ -f "$session/files" ] || exit 0
    conflicts=0
    while IFS= read -r rel; do
        dst="$sd/$rel";old="$session/original/$rel"
        if [ ! -f "$old" ] && [ ! -f "$session/absent/$rel" ]; then continue; fi
        if [ -f "$dst" ] && [ -f "$old" ] && cmp -s "$dst" "$old"; then continue; fi
        if [ -f "$dst" ] && [ -f "$session/applied/$rel" ] && cmp -s "$dst" "$session/applied/$rel"; then
            if [ -f "$old" ]; then cp "$old" "$dst.overlay-tmp";mv "$dst.overlay-tmp" "$dst"; else rm -f "$dst"; fi
        elif [ ! -e "$dst" ] && [ -f "$session/absent/$rel" ]; then
            :
        else
            echo "Kept later edit or missing file: $rel";conflicts=1
        fi
    done < "$session/files"
    [ "$conflicts" != 0 ] || touch "$session/restored"
    sync
    exit "$conflicts"
fi
stage=asset_checks
for kind in tv lcd crt; do
    [ -s "$app/assets/$res/$kind.png" ] && [ -s "$app/assets/$res/$kind.cfg" ] || fail "Missing $res/$kind assets; copy the full App folder"
done
[ -s "$app/filters/crt.filt" ] && [ -s "$app/filters/mini_flip_crt.so" ] || fail "Missing CRT filter; copy the full App folder"
# Stable paths let changing hardware resolution select the right native PNG
# without overwriting any game overrides or user changes at each boot.
if [ "$(cat "$app/current/resolution" 2>/dev/null || true)" != "$res" ]; then
    mkdir -p "$app/current"
    for leaf in tv.png tv.cfg lcd.png lcd.cfg crt.png crt.cfg; do
        cp "$app/assets/$res/$leaf" "$app/current/$leaf.tmp"
        mv "$app/current/$leaf.tmp" "$app/current/$leaf"
    done
    echo "$res" > "$app/current/resolution.tmp"
    mv "$app/current/resolution.tmp" "$app/current/resolution"
fi
[ "$action" != boot ] || exit 0
[ -s "$sd/RetroArch/.retroarch/retroarch.cfg" ] || fail "Missing RetroArch/.retroarch/retroarch.cfg"
stage=manifest
if [ "$cycle" = 0 ] || [ -f "$session/restored" ]; then
    cycle=$((cycle+1));session="$state/snapshot-$cycle";mkdir -p "$session"
    echo "$cycle" > "$state/active.tmp";mv "$state/active.tmp" "$state/active"
fi
if [ "$action" = apply ]; then
    {
        [ ! -f "$session/files" ] || cat "$session/files"
        echo 'RetroArch/.retroarch/retroarch.cfg'
        (cd "$sd" && find Saves/CurrentProfile/config -type f -name '*.cfg')
        (cd "$sd" && find Saves/CurrentProfile/config -type f -path '*/Snes9x/*.opt')
        if [ -d "$sd/.tmp_update/res/display/profiles" ]; then
            (cd "$sd" && find .tmp_update/res/display/profiles -type f -name '*.cfg')
        fi
        # Seed the actual PS1 core names as well as handheld overrides. All
        # other RetroArch cores inherit the global TV overlay if unconfigured.
        while IFS= read -r core; do
            echo "Saves/CurrentProfile/config/$core/$core.cfg"
            for resolution in 752x560 640x480; do
                for mode in balanced clean; do
                    echo ".tmp_update/res/display/profiles/$resolution/$mode/$core/$core.cfg"
                done
            done
        done < "$app/cores.txt"
        [ ! -f "$sd/Emu/NDS/resources/settings.json" ] || echo 'Emu/NDS/resources/settings.json'
    } | sort -u | awk '!seen[tolower($0)]++' > "$session/files.tmp"
    mv "$session/files.tmp" "$session/files"
fi
nds_ready=0
stage=optional_DS_check
if grep -q '^Emu/NDS/' "$session/files"; then
    jq=${MINIFLIP_JQ:-$sd/.tmp_update/bin/jq}
    if [ -x "$jq" ] && "$jq" -e 'type == "object" and has("overlay")' "$sd/Emu/NDS/resources/settings.json" >/dev/null; then
        nds_ready=1
    else
        echo "NOTE: DS settings skipped; JSON tool or settings unavailable. Console overlays will still apply."
    fi
fi
while IFS= read -r rel; do
    stage="configuration: $rel"
    if [ "$rel" = Emu/NDS/resources/settings.json ] && [ "$nds_ready" != 1 ]; then continue; fi
    dst="$sd/$rel"
    kind=tv
    case "$rel" in
        */Snes9x/*.opt) kind=options ;;
        *PCSX*|*SwanStation*|*DuckStation*|*/PSX.cfg) kind=off ;;
        */Gambatte/*|*/gpSP/*|*/Beetle\ GBA/*|*/VBA-M/*|*/VBA\ Next/*|*/Beetle\ NeoPop/*|*/mGBA/GBA.cfg) continue ;;
        */profiles/*/clean/*) kind=off ;;
        */Handy/*|*/Beetle\ Lynx/*|*/Beetle\ WonderSwan/*|*/PokeMini/*|*/Potator/*|*/SameDuck/*|*/TGB\ Dual/*|*/Gearboy/*|*/Meteor/*|*/Game\ \&\ Watch/*|*/GW/*|*/VecX/*|*/vecx/*|*/Arduous/*|*/Mu/*|*/VeMUlator/*|*/SquirrelJME/*|*/mGBA/*|*/GG.cfg) kind=lcd ;;
        */FCEUmm/*|*/Supafaust/*|*/Beetle\ Supafaust/*|*/Snes9x*/*|*/PicoDrive/*|*/Genesis\ Plus\ GX/*|*/Gearsystem/*|*/Beetle\ PCE*/*|*/Beetle\ SuperGrafx/*) kind=crt ;;
    esac
    mkdir -p "$(dirname "$dst")" "$session/original/$(dirname "$rel")" "$session/absent/$(dirname "$rel")" "$session/applied/$(dirname "$rel")"
    if [ ! -f "$session/original/$rel" ] && [ ! -f "$session/absent/$rel" ]; then
        if [ -f "$dst" ]; then cp "$dst" "$session/original/$rel.tmp";mv "$session/original/$rel.tmp" "$session/original/$rel";
        else touch "$session/absent/$rel"; fi
    fi
    if [ "$rel" = Emu/NDS/resources/settings.json ]; then
        "$jq" '.overlay = 1' "$dst" > "$dst.overlay-tmp"
    elif [ "$kind" = options ]; then
        awk '{ k=$0; sub(/=.*/,"",k); gsub(/[ \t\r]/,"",k); if(k!="snes9x_overscan") print }' "$dst" > "$dst.overlay-tmp"
        echo 'snes9x_overscan = "disabled"' >> "$dst.overlay-tmp"
    else
        enabled=true;overlay="/mnt/SDCARD/App/AllOverlays/current/$kind.cfg"
        if [ "$kind" = off ]; then enabled=false;overlay=''; fi
        # Only overlay keys: retain scaling, filters, audio, input and paths.
        if [ -f "$dst" ]; then
            awk -v kind="$kind" '{ k=$0; sub(/=.*/,"",k); gsub(/[ \t\r]/,"",k);
                if (kind=="crt" && k ~ /^(video_filter|video_scale_integer|video_dingux_ipu_keep_aspect|video_dingux_ipu_filter_type|video_crop_overscan|video_shader_enable)$/) next;
                if (k !~ /^(input_overlay|input_overlay_enable|input_overlay_enable_autopreferred|input_overlay_opacity|input_overlay_auto_scale|input_overlay_auto_rotate|input_overlay_hide_in_menu|input_overlay_hide_when_gamepad_connected)$/) print }
            ' "$dst" > "$dst.overlay-tmp"
        else : > "$dst.overlay-tmp"; fi
        cat >> "$dst.overlay-tmp" <<EOF
input_overlay = "$overlay"
input_overlay_enable = "$enabled"
input_overlay_enable_autopreferred = "false"
input_overlay_opacity = "1.0"
input_overlay_auto_scale = "false"
input_overlay_auto_rotate = "false"
input_overlay_hide_in_menu = "true"
input_overlay_hide_when_gamepad_connected = "false"
EOF
        if [ "$kind" = crt ]; then
            cat >> "$dst.overlay-tmp" <<EOF
video_filter = "/mnt/SDCARD/App/AllOverlays/filters/crt.filt"
video_scale_integer = "false"
video_dingux_ipu_keep_aspect = "false"
video_dingux_ipu_filter_type = "1"
video_crop_overscan = "false"
video_shader_enable = "false"
EOF
        fi
    fi
    mv "$dst.overlay-tmp" "$dst"
    cp "$dst" "$session/applied/$rel.tmp";mv "$session/applied/$rel.tmp" "$session/applied/$rel"
done < "$session/files"
touch "$state/enabled"
sync
echo "Applied all-system overlays ($res), PS1 excluded. Backups: $session/original"
