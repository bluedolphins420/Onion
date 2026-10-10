# CRT Overlay

This Retroarch overlay is designed for the Miyoo Mini V4. It enhances any core that emulates a system which benefits from a CRT look.
It includes a custom filter which ensures that the image has the correct resolution for this overlay on every system.

The overlay in the 'edge_fix' folder includes one row of black pixels at the top which fixes a rare screen issue for some devices.

## Recommended Settings

### Settings

Path: Main Menu / Settings / Video

- Scaling
  - Integer Scale: Off
  - Keep Aspect Ratio: Off
  - Crop Overscan: Off
- Image Interpolation: Bilinear
- Video Filter: crt
  (the filter that comes with this overlay)
-> Main Menu / Quick Menu / Overrides / Save Content Directory Overrides

### Core Options

Path: Main Menu / Quick Menu / Core Options

The exact settings depend on the core and generally do not affect the overlay. The only important thing is to not apply any overscan in the core settings. Let the filter handle it.



