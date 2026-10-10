# Nintendo Game Boy Advance Overlay

This Retroarch overlay is designed for the Miyoo Mini V4. It works for any core that emulates the Nintendo Game Boy Advance.

The overlay is intended to be used at 100 % opacity. If you desire a different grid strength, select one from the 'extra' folder.
The overlays in the 'edge_fix' folder include one row of black pixels at the top which fixes a rare screen issue for some devices.

## Recommended Settings

### Settings

Path: Main Menu / Settings / Video

- Scaling
  - Integer Scale: On
  - Keep Aspect Ratio: On
  - Crop Overscan: Off
- Image Interpolation: Bicubic
- Video Filter: Offset_Custom / Offset_up10px
-> Main Menu / Quick Menu / Overrides / Save Content Directory Overrides

### Core Options (gpSP)

Path: Main Menu / Quick Menu / Core Options

- Color Correction: On
- Interframe Blending: On
-> Manage Core Options / Save Content Directory Options

### Core Options (mGBA)

Path: Main Menu / Quick Menu / Core Options

- Video / Color Correction: Game Boy Advance
- Video / Interframe Blending: Simple
-> Manage Core Options / Save Content Directory Options

