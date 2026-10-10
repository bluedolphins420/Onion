# Nintendo Game Boy Overlay

This Retroarch overlay is designed for the Miyoo Mini V4 running the Gambatte core emulating the Nintendo Game Boy.

The overlay is intended to be used at 100 % opacity. If you desire a different grid strength, select one from the 'extra' folder.
The overlays in the 'edge_fix' folder include one row of black pixels at the top which fixes a rare screen issue for some devices.

## Recommended Settings

### Settings

Path: Main Menu / Settings / Video

- Scaling
  - Integer Scale: Off
  - Keep Aspect Ratio: On
  - Crop Overscan: Off
- Image Interpolation: Bicubic
- Video Filter: None
  (select 'Remove Video Filter' if a filter is enabled)
-> Main Menu / Quick Menu / Overrides / Save Content Directory Overrides

### Core Options

Path: Main Menu / Quick Menu / Core Options

- GB Colorization: internal / use color categories
- Current category color for palettes: Essentials
  - Color Categories: Essentials - GB-DMG
- Color Correction: OFF
- Dark Filter Level (%): 0
- Interframe Blending: Simple
-> Manage Core Options / Save Content Directory Options

## Credit

Thanks to mugwomp93 for the Game Boy bezel.
See his project at https://github.com/mugwomp93/muOS_Customization.
