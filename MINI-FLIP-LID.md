# Mini Flip lid standby patch

Base: OnionUI/Onion commit 07505ea, version 4.4.0-beta-20260120.
This is a source implementation; no successful ARM build or device test has
been performed yet. Do not treat the source checkout as an installable release.

The Mini Flip exposes its hall sensor at
`/sys/devices/soc0/soc/soc:hall-mh248/hallvalue` (0 closed, 1 open), as used
by https://github.com/Surwish/Onion/tree/Miyoo-Mini-Flip-compatibility.
The patch enables itself only when that file supplies a valid reading.
No model ID or firmware flash is required. Missing sensor support leaves the
existing power-button sleep behavior in place.

## Behavior

- Poll the sensor every 100 ms and require 200 ms of stable readings.
- Close to enter Onion standby; open to resume. This pauses applications,
  mutes sound, disables the display and enables Onion power saving. It is
  not kernel suspend-to-RAM.
- Power/menu presses cannot wake a closed device. The hardware emergency
  power-off remains a firmware function.
- Preserve the current beta's sleep timeout: a manual/lid sleep uses the
  configured sleep timer plus one minute before save-and-shutdown. Timer 0
  disables timed shutdown. Charging inhibits timed shutdown.
- Preserve the stay_awake flag's existing behavior, including apps that
  deliberately keep running while the display is off.
- Reset inactivity after lid wake to avoid immediately sleeping again.
- Re-enter standby if an emulator refuses automatic save-and-shutdown.

## Build

Publish this checkout to your GitHub fork. Under Actions, run **Build Mini Flip
lid patch**. It first runs the debounce test, then builds `keymon` with the
upstream Miyoo toolchain. Download the artifact only after both jobs pass.
Alternatively, use the upstream toolchain container to run:

```sh
source /root/.bashrc
mkdir -p "$PWD/lid-patch/.tmp_update/bin"
make -C src/keymon BUILD_DIR="$PWD/lid-patch/.tmp_update/bin"
```

## Install a successfully built artifact

Power off and back up the SD card, including saves. Keep a copy of the original
`.tmp_update/bin/keymon` for rollback. Extract the artifact and merge its
`.tmp_update` folder into the SD card root, replacing only `bin/keymon`.
This patch targets the exact beta above; it does not replace the stock firmware.
To roll back, power off and restore the original `keymon`.

## Device checks still required

1. Verify that the sensor file changes from 1 to 0 when closing the lid.
2. Close/open in MainUI and RetroArch. Confirm screen off, silent audio,
   paused game and normal sound/display on resume.
3. Repeat with sleep timer 0. The game must pause despite no shutdown timer.
4. With a nonzero timer, leave closed beyond timer plus one minute; confirm
   save-and-shutdown and correct game resume after boot.
5. Check charging, rapid lid movements, ordinary power-button sleep while
   the lid is open, and closing/opening during power-button standby.
6. Verify a core with auto-save disabled remains paused after timeout.
7. Test standalone apps separately; their save/shutdown support varies.
8. Check temperature and battery drain during standby before pocket use.

If the sensor file is absent, collect the stock firmware version from the
device's About/System information and inspect its input devices before
changing this implementation.
