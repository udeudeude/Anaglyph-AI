# Anaglyph & Friends

> GitHub repository name: `Anaglyph-AI`  
> Current application name: **Anaglyph & Friends**

Anaglyph & Friends converts a single 2D image into several stereoscopic products using a Depth Anything V2 monocular depth estimate:

1. **Red/cyan anaglyph** for red-cyan glasses.
2. **Parallel stereo pair** with left-eye view on the left.
3. **Cross-eyed stereo pair** with the views swapped.
4. **Individual left-eye and right-eye views**.
5. **Depth-map data**, including a full-resolution 16-bit grayscale PNG and float32 NumPy array.

The original Anaglyph AI project and hosted demonstration were created by **Duy Huynh**. This repository version extends the original application for local/offline stereoscopic experimentation.

## Current interface

The local frontend is a dark desktop-style workspace with:

- drag-and-drop, file-picker, and clipboard-paste image loading;
- full-resolution source retention;
- source and depth-map inspection views;
- a resizable/collapsible source sidebar;
- tabs for Red/Cyan, Parallel, and Cross-Eyed output;
- independent on-screen stereo-pair sizing;
- zoom and pan for preview inspection;
- fullscreen viewing on black;
- JPEG or PNG full-resolution downloads;
- adjustable JPEG quality;
- individual left/right-eye downloads;
- downloadable 16-bit and raw float32 depth maps;
- browser-local persistence for viewing/render settings.

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

## Full-resolution architecture

Earlier versions resized uploaded images to a maximum dimension of 1500 pixels. The current version does **not** do that. The original decoded image is retained at its full pixel dimensions.

The application now separates interactive viewing from final rendering:

1. Upload and retain the full-resolution source.
2. Estimate a normalized depth map with Depth Anything V2 and retain it as float32 data at source dimensions.
3. Build one smaller cached left/right pair for interactive previews.
4. Derive red/cyan, parallel, and cross-eyed previews from that same cached pair.
5. On the first download for the current stereo settings, build one full-resolution left/right pair.
6. Reuse that full-resolution pair for anaglyph, parallel, cross-eyed, left-eye, and right-eye downloads.

This avoids recalculating stereo geometry separately for each output while keeping ordinary interface changes practical on an older CPU.

## Processing controls

- **3D strength** sets maximum stereo disparity from 0% to 6% of image width. Dragging the slider does not continually regenerate; the new value is applied when the control is released.
- **Pop Out** changes the depth/disparity orientation.
- **Reduce retinal rivalry** changes only the red/cyan combination. It reuses the existing stereo pair rather than rebuilding stereo geometry.
- **On-screen pair size** changes only display size, never downloadable resolution.

## Depth-map downloads

The source sidebar exposes:

- **16-bit depth PNG**: full source dimensions, normalized 0–65535 depth values;
- **Raw float32**: the normalized depth array in NumPy `.npy` format;
- **Color map**: the colored visualization used by the interface.

The float32/16-bit products are preferable to the colored visualization for future image-processing work.

## How conversion works

The processing pipeline is:

`single image -> Depth Anything V2 -> normalized depth -> synthetic left/right views -> selected stereo presentation`

Depth Anything V2 estimates depth from one image. The stereo renderer converts normalized depth into horizontal disparity, creates synthetic left/right views, and uses OpenCV Telea inpainting to fill holes revealed by displaced foreground objects.

A monocular source does not contain genuinely hidden surfaces, so synthesized stereo will inevitably have limitations around occlusion boundaries.

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

The requirements now use the stack successfully tested on the 2015 Intel MacBook Pro used for this project:

- Python 3.10.4
- PyTorch 2.2.2
- torchvision 0.17.2
- NumPy 1.26.4

The Flask backend defaults to `http://localhost:8000`. Debug/reloader mode is off by default to avoid loading the AI model twice on an older machine.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite normally serves the interface at `http://localhost:5173` and talks to `http://localhost:8000` by default.

## Important backend endpoints

- `POST /image` — retain a full-resolution source image.
- `GET /depth-map` — estimate depth if needed and return the colored preview.
- `GET /depth-map/download?kind=gray16` — full-resolution 16-bit depth PNG.
- `GET /depth-map/download?kind=npy` — full-resolution float32 depth array.
- `GET /render` — build/cache the interactive stereo preview pair.
- `GET /prepare-full` — build/cache a full-resolution stereo pair for current settings.
- `GET /output/<kind>` — return `anaglyph`, `parallel`, `cross`, `left`, or `right` from the cached stereo pair.

Legacy `/anaglyph` and `/stereo-pair` routes remain for compatibility.

## Deferred larger features

Three larger directions are intentionally **not part of this upgrade pass**:

- editable depth maps;
- phantogram rendering;
- packaging as a standalone double-clickable macOS application.

They remain natural future extensions, but the current goal is to keep the working local web application stable while improving its everyday stereo workflow.
