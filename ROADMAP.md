# Anaglyph & Friends Roadmap

This file tracks ideas that are intentionally **not** part of the current implementation pass, so they do not disappear into chat history.

## Explicitly deferred larger projects

1. **Editable depth maps**
   - paint/erase depth corrections
   - levels/contrast/blur controls
   - local masking and edge cleanup
   - preserve/export edited high-bit-depth depth data

2. **Phantogram mode**
   - viewing-plane and camera/viewer geometry
   - perspective remapping for tabletop/oblique viewing
   - print calibration and physical-size-aware output

3. **Packaged macOS application**
   - double-click launch
   - bundle/start local backend automatically
   - eliminate Terminal setup for normal use
   - eventually consider signing/notarization and Intel/Apple Silicon packaging

## Potential future viewing / export techniques

- **MPO / stereo JPEG** for devices and software that store both eye views in one file.
- **Full-SBS, half-SBS, and over/under VR exports** beyond the current Cardboard-oriented presentation.
- **Row/column interlaced stereo** for passive 3D displays and some legacy televisions/monitors.
- **Checkerboard stereo** for compatible legacy projectors/televisions.
- **Pulfrich animation** using generated horizontal motion for dark-filter Pulfrich viewing.
- **Additional autostereoscopic display profiles** when a specific display/panel is available for calibration.
- **Additional historical stereograph templates**, typography, backs, publisher marks, numbering, and batch card generation.
- **Additional phone/viewer profiles** with saved device dimensions and optional lens-distortion correction.
- **Saved lenticular printer + paper + sheet profiles** once real calibration data is available.

## Current-pass techniques

The current application pass covers:

- red/cyan anaglyph
- parallel stereo
- cross-eyed stereo
- ChromaDepth
- Cardboard / phone viewer presentation
- traditional stereoscope cards with arched images and text
- wiggle-grams
- random-dot autostereograms
- pattern-based autostereograms
- lenticular 3D interlacing plus printable LPI calibration bars

Device- or print-specific modes expose their extra information only when that technique is selected and begin with practical default presets rather than empty fields.
