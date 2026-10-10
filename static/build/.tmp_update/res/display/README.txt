Mini Flip display defaults v1. Original generated artwork; GPL-3.0-or-later,
matching the Onion project. Source: tools/generate_display_profiles.py.
No third-party bezel artwork is redistributed by this addition.

Balanced: GB/GBC, GBA and NGP use integer scaling, subtle aligned grids and
neutral bezels; TV cores use bicubic scaling and a subtle screen-space
scanline texture (not an emulation of a specific CRT). PS1/arcade/computers
use clean scaling without additional software filters. Clean removes the
overlays while retaining the scaling choices. Frame rate/battery improvement
is not measured. DraStic and standalone emulators retain their own defaults.

Driver constants verified at RetroArch 69a4f0ea: 0=bicubic, 1=bilinear,
2=nearest. Miyoo integer scaling uses the source dimensions; no custom
viewport settings or shader presets are assumed. 480p has separate assets.
GBA 560p viewport: 720x480 at 16,40. GB/GBC: 480x432 at 136,64.
NGP: 480x456 at 136,52. Core output changes/rotation/game overrides may require
an individual override; these are defaults, not universal game certification.
