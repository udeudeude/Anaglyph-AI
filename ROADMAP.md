# Anaglyph & Friends Roadmap

This file tracks ideas that are intentionally **not** part of the current implementation, so they do not disappear into chat history.

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
- **Pulfrich animation** using generated horizontal motion for dark-filter Pulfrich viewing.
- **Additional autostereoscopic display profiles** when a specific display/panel is available for calibration.
- **Additional historical stereograph templates**, typography, backs, publisher marks, numbering, and batch card generation.
- **Additional phone/viewer profiles** with saved device dimensions and optional lens-distortion correction.
- **Saved lenticular printer + paper + sheet profiles** once real calibration data is available.
- **More specialized legacy/display encodings** when a concrete device or workflow calls for them.

## Implemented technique families

The current application includes:

- **Anaglyph**
  - red/cyan
  - red/green
  - red/blue
  - full-color, half-color, and grayscale rendering
- parallel stereo
- cross-eyed stereo
- ChromaDepth
- Cardboard / phone viewer presentation
- traditional stereoscope cards with arched images and text
- wiggle-grams
- random-dot autostereograms
- pattern-based autostereograms
- lenticular 3D interlacing plus printable LPI calibration bars

### Lower-priority display / compatibility formats

These are intentionally placed behind the main technique chooser so they do not compete visually with the primary viewing methods:

- half-width side-by-side
- top/bottom stereo
- row-interlaced stereo
- column-interlaced stereo
- checkerboard stereo

## Depth-source workflow

The visible photograph and the depth source can now be independent.

- Depth Anything V2 remains the default depth source.
- A replacement depth map can be imported from PNG/JPEG/TIFF/WebP or float32 `.npy` data.
- Imported maps do not need to match the source image dimensions or aspect ratio.
- Aspect matching options include crop-to-fill, fit-inside, and stretch-to-image.
- Near/far depth can be inverted.
- Switching the active depth source invalidates the stereo cache and all techniques use the newly selected map.

Device- or print-specific modes expose their extra information only when that technique is selected and begin with practical default presets rather than empty fields.
