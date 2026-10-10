Mini Flip display defaults v3: OzBoss edition.
GB/GBC/GBA use the original OzBoss 752x560 artwork and recommended settings.
GB/GBC: bicubic 622x560 at x64,y0, no crop. GBA: 3x 720x480 at x16,y10,
using Onion's bundled Offset_Custom/Offset_up10px filter. Opacity is 1.0.
GB and GBC use separate ROM-directory profiles (Roms/GB and Roms/GBC).
Nested/mixed folders fall back to core settings; save a directory override
if you organize ROMs in subfolders. mGBA's GBA overlay is directory-only,
because that core also runs GB/SGB. Other GBA-only cores receive the bezel
but retain their stock core options. Gambatte/gpSP/mGBA options are seeded
from stock with the author's color/blending choices for GB/GBC/GBA.

The first boot archives all old CFG overrides and OPT overrides for
Gambatte, gpSP and mGBA, then installs these defaults. Other core options,
controls/remaps and saves are retained. Backups: Saves/CurrentProfile/
.mini-flip-display-v3/snapshot-N/archive. Earlier v2 snapshots remain intact.
Later manual changes persist. Apps: Balanced display reapplies the profiles;
Clean display removes overlays and GBA offset; Restore display restores the
pre-update snapshot, leaving conflicting later edits for manual resolution.

480p mode uses separate original neutral assets; OzBoss grids are never
resized. NGP and TV defaults retain the prior neutral profiles. CRT is an
optional original preset, with its matching ARM filter and readme under
.tmp_update/res/display/ozboss/crt. In RetroArch select crt/crt.cfg as overlay,
crt/filter/crt.filt as video filter; integer and keep-aspect OFF, bilinear,
crop overscan OFF, opacity 1.0. Disable core overscan as its readme requires.
It deliberately crops/pads to normalize image geometry. It is not enabled
globally, especially for variable-resolution, interlaced or rotated content.
The third-party CRT binary is supplied as downloaded; hardware validation
is pending. Original edge-fix/extra-strength variants are not installed.

Artist credits, original readmes and asset checksums: ozboss/.
No GPU shaders, overclock or emulator binary changes. No measured FPS or
battery claims. Standalone emulators (including DraStic) keep their settings.
