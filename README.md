# Anaglyph & Friends

> GitHub repository name: `Anaglyph-AI`  
> Current application name: **Anaglyph & Friends**

Anaglyph & Friends turns one ordinary photograph into a growing collection of stereoscopic, autostereoscopic, viewer-specific, animated, and print-oriented 3D formats using a **Depth Anything V2** monocular depth estimate.

The original Anaglyph AI project and hosted demonstration were created by **Duy Huynh**. This repository version extends the original application for local/offline stereoscopic experimentation.

## Current techniques

### Direct stereo / glasses

- **Red/cyan anaglyph**
- **Parallel stereo**
- **Cross-eyed stereo**
- **ChromaDepth**, with depth-coded spectral color while retaining image brightness

### Viewer formats

- **Cardboard / phone VR viewer**
  - Google Cardboard-style starting preset
  - generic phone-viewer preset
  - editable screen resolution, physical screen width, lens-center separation, and image fill
- **Traditional stereoscope card**
  - Holmes-style 7 × 3.5 inch starting preset
  - traditional arched photograph tops
  - configurable print DPI, card/image dimensions, spacing, mount color, and arch depth
  - title, caption, and publisher/credit text rendered directly onto the card

### Autostereograms

- **Random-dot stereogram**
  - parallel or cross-eyed interpretation
  - dot size, separation, depth strength, and monochrome/color dots
- **Pattern stereogram**
  - built-in repeating geometric texture
  - optional user-uploaded pattern image
  - parallel/cross-eyed and depth/separation controls

### Animation

- **Wiggle-gram**
  - multiple synthesized virtual viewpoints rather than simple left/right alternation
  - configurable viewpoint count and frame timing
  - looping GIF output

### Lenticular print

- **Lenticular 3D interlacing**
  - 60 LPI / 600 DPI / 6-view starting preset
  - 50 LPI and 40 LPI starting presets
  - editable printer DPI, measured LPI, physical print size, number of views, and lenticule slant
  - multi-view synthesis from the AI depth map
  - printable **black/white calibration bars** across a user-selected LPI range
  - calibration PNG includes DPI metadata; print it at **100% / Actual Size with all fit-to-page scaling disabled**

Device- and print-specific information is deliberately hidden until that technique is selected. Each such mode opens with a practical standard starting point rather than an empty form.

## Interface

The local frontend is a dark desktop-style workspace with:

- drag-and-drop, file-picker, and clipboard-paste image loading;
- full-resolution source retention;
- source and depth-map inspection views;
- a resizable/collapsible source sidebar;
- fast Red/Cyan, Parallel, and Cross-Eyed controls plus a grouped **More techniques** selector;
- technique-specific configuration panels that appear only when relevant;
- explicit **Apply settings** behavior for specialized techniques, avoiding accidental expensive re-renders while editing parameters;
- independent on-screen preview sizing;
- zoom and pan for preview inspection;
- fullscreen viewing on black;
- full-quality downloads;
- individual left/right-eye downloads for stereo-based techniques;
- downloadable 16-bit and raw float32 depth maps;
- browser-local persistence for rendering, viewer, and print settings.

### Keyboard shortcuts

There is intentionally **no global regenerate shortcut**.

| Key | Action |
| --- | --- |
| `R` | Red/cyan anaglyph |
| `V` | Parallel view |
| `X` | Cross-eyed view |
| `F` | Fullscreen selected output |
| `D` | Download selected output |
| `U` | Open image chooser |
| `Command-V` | Paste an image using the normal macOS paste action |

No casual keyboard shortcut changes stereo strength, Pop Out, lenticular calibration, or other rendering parameters.

## Full-resolution architecture

Earlier versions resized uploads to a maximum dimension of 1500 pixels. The current application does **not** discard the original resolution.

The pipeline now separates interactive previews from final rendering:

1. Retain the decoded source at original pixel dimensions.
2. Estimate and retain a normalized source-size depth map.
3. Build smaller interactive products when a technique permits it.
4. Cache the ordinary left/right stereo pair for reuse by Red/Cyan, Parallel, Cross-Eyed, Cardboard, stereoscope, and eye-view exports.
5. Create final static downloads from the full-resolution source or, for physical print techniques, from the requested print dimensions and DPI.

Special formats such as wiggle-grams, autostereograms, ChromaDepth, and lenticular interlacing reuse the same source/depth foundation but have their own rendering modules.

## Shared stereo controls

Stereo-based techniques expose:

- **3D strength**, maximum disparity from 0% to 6% of image width;
- **Pop Out**, changing the depth/disparity orientation;
- **On-screen preview size**, which affects only display size and never download resolution.

The Red/Cyan technique additionally offers **Reduce retinal rivalry**.

## Depth-map downloads

The source sidebar exposes:

- **16-bit depth PNG**: full source dimensions, normalized 0–65535 depth values;
- **Raw float32**: normalized depth in NumPy `.npy` format;
- **Color map**: the colored visualization used by the interface.

The float32/16-bit products are preferable to the colored visualization for future image-processing work.

## How conversion works

Core pipeline:

`single image -> Depth Anything V2 -> normalized depth -> selected 3D renderer / presentation`

For ordinary stereo formats, normalized depth becomes horizontal disparity, creating synthetic left/right views. OpenCV Telea inpainting fills holes revealed by displaced foreground objects.

A monocular source does not contain genuinely hidden surfaces, so generated views inevitably have limitations around occlusion boundaries.

The newer technique renderers build on the same depth map:

- ChromaDepth maps near/far depth into spectral color;
- autostereograms vary repeating-pattern separation by depth;
- wiggle-grams synthesize a sequence of virtual camera offsets;
- lenticular output synthesizes several viewpoints and interlaces them according to printer DPI and calibrated lenticular pitch.

## Local/offline operation

Once dependencies, Depth Anything V2 source, and its checkpoint are installed, image processing works without an Internet connection.

The backend expects:

```text
backend/ai_models/Depth_Anything_V2/depth_anything_v2/...
backend/ai_models/checkpoints/depth_anything_v2_vits.pth
```

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The requirements use the stack successfully tested on the 2015 Intel MacBook Pro used for this project:

- Python 3.10.4
- PyTorch 2.2.2
- torchvision 0.17.2
- NumPy 1.26.4

The Flask backend defaults to `http://localhost:8000`. Debug/reloader mode is off by default so the AI model is not loaded twice on an older machine.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite normally serves the interface at `http://localhost:5173` and talks to `http://localhost:8000` by default.

## Important backend endpoints

Core:

- `POST /image` — retain the full-resolution source.
- `POST /pattern` — store an optional texture for pattern stereograms.
- `GET /depth-map` — return the colored depth preview.
- `GET /depth-map/download?kind=gray16|npy|color` — depth-map exports.
- `GET /render` — build/cache the interactive ordinary stereo pair.
- `GET /prepare-full` — build/cache a full-resolution ordinary stereo pair.
- `GET /output/<kind>` — `anaglyph`, `parallel`, `cross`, `left`, or `right`.

Technique renderers:

- `GET /special/chromadepth`
- `GET /special/cardboard`
- `GET /special/stereoscope`
- `GET /special/wiggle`
- `GET /special/autostereogram?style=random|pattern`
- `GET /special/lenticular`
- `GET /lenticular/calibration`

Legacy `/anaglyph` and `/stereo-pair` routes remain for compatibility.

## Project structure

```text
backend/
  app.py
  depth_map_generator.py
  anaglyph_generator.py
  technique_generator.py       specialized viewer / print / animation renderers
frontend/src/
  App.tsx
  ImageUpload.tsx
  AnaglyphEditor.tsx           technique-studio orchestration
  TechniqueControls.tsx        conditional device/print/technique settings
  techniques.ts                technique definitions and starting presets
ROADMAP.md                      deliberately deferred and potential future techniques
```

## Future work

See **[ROADMAP.md](ROADMAP.md)**. The larger items explicitly deferred from this pass are editable depth maps, phantograms, and packaging as a double-clickable macOS application. Additional possible formats such as MPO, interlaced/checkerboard stereo, Pulfrich animation, and broader VR exports are recorded there rather than being lost in conversation history.
