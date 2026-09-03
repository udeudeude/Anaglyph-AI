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

4. **Independent transparent 3D foreground layers**
   - import a transparent PNG as a movable object over the base photograph
   - estimate or import a separate depth map for that foreground object
   - synthesize the layer stereoscopically as well as the base image
   - move, scale, rotate, and position the object interactively in the composition
   - control where the object sits in scene depth so it can appear in front of or behind existing geometry
   - preserve alpha edges cleanly in generated left/right views and final techniques
   - potentially support multiple independent 3D layers later

## Documentation / onboarding

- **Add helpful screenshots to the README and beginner setup instructions.**
  - show the GitHub **Code** / clone step
  - show the two-Terminal backend/frontend setup
  - show a successfully running local app in the browser
  - include only screenshots that clarify steps where a new GitHub/Terminal user could otherwise get lost

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
  - adjustable color retention from full color through grayscale
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
