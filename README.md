# Anaglyph AI

Anaglyph AI converts a single 2D (monocular) image into three stereoscopic 3D output formats:

1. **Red/cyan anaglyph** for red-cyan glasses.
2. **Parallel stereo pair** (left-eye image on the left, right-eye image on the right) for relaxed/wall-eyed free viewing.
3. **Cross-eyed stereo pair** (right-eye image on the left, left-eye image on the right) for cross-eyed free viewing.

The project uses **Depth Anything V2** to estimate a depth map from the source image, then synthesizes left- and right-eye views from that depth data. The three output formats are different presentations of the same generated stereo pair.

The original project and hosted demonstration were created by **Duy Huynh**. The original hosted version is at [anaglyph-ai.com](https://anaglyph-ai.com). This repository version extends the output stage to include downloadable parallel and cross-eyed stereo pairs in addition to the original anaglyph.

## What the application does

The processing pipeline is:

`single 2D image -> Depth Anything V2 depth map -> synthetic left/right views -> chosen 3D output`

The interface displays the uploaded image and estimated depth map, then generates all three 3D formats. Each result has its own **Download** button.

### Controls

- **Strength** sets maximum stereo disparity as a percentage of image width, from 0% to 6%.
- **Pop Out** changes the zero-parallax placement so the stereo effect is biased toward appearing in front of rather than behind the display plane.
- **Minimise Retinal Rivalry** applies the existing optimized color transformation to the red/cyan anaglyph only. It does not alter the parallel or cross-eyed stereo pairs.

## Output formats

### Red/cyan anaglyph

The left and right stereo views are combined into color channels so each eye receives a different view through red-cyan glasses. The optional retinal-rivalry reduction uses optimized color matrices based on the Dubois approach.

### Parallel stereo

The output is a single side-by-side JPEG arranged:

`LEFT EYE | RIGHT EYE`

It is intended for parallel (wall-eyed) free viewing, in which the eyes converge less than they would on the physical image plane.

### Cross-eyed stereo

The same stereo pair is saved in the opposite order:

`RIGHT EYE | LEFT EYE`

It is intended for cross-eyed free viewing.

## How the 3D conversion works

### 1. Depth estimation

The backend uses [Depth Anything V2](https://github.com/DepthAnything/Depth-Anything-V2), an open-source monocular depth-estimation model. The current code loads the **ViT-S (`vits`)** model.

At runtime PyTorch chooses an available compute device in this order:

1. CUDA, when an NVIDIA CUDA device is available.
2. Apple MPS, when supported.
3. CPU otherwise.

That means an Intel Mac uses the CPU path.

### 2. Stereo image synthesis

The normalized depth map is converted into horizontal pixel shifts. Near and far pixels receive different shifts, producing synthetic left-eye and right-eye views. Because a single photograph does not contain the surfaces hidden behind foreground objects, shifting pixels creates holes near depth discontinuities. The project fills those holes with OpenCV's Telea inpainting method.

### 3. Output rendering

The left/right views are then either:

- merged into a red/cyan anaglyph,
- concatenated left-to-right for parallel viewing, or
- concatenated in reversed order for cross-eyed viewing.

## Local and offline use

The application can run locally. Once the software dependencies, Depth Anything V2 source, and model checkpoint are present on the computer, image processing does **not** require an Internet connection.

The backend expects the model code and checkpoint at these paths relative to `backend/`:

```text
ai_models/Depth_Anything_V2/depth_anything_v2/...
ai_models/checkpoints/depth_anything_v2_vits.pth
```

The checkpoint is intentionally not stored in Git because model files are large.

### Backend

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Place the Depth Anything V2 source under `backend/ai_models/Depth_Anything_V2/` and the ViT-S checkpoint at `backend/ai_models/checkpoints/depth_anything_v2_vits.pth`, then start Flask:

```bash
python app.py
```

The backend defaults to `http://localhost:8000`.

> **Intel Mac note:** the inference code has a CPU fallback. PyTorch/Python package compatibility varies by macOS and Python version, so an Intel Mac may require a compatible CPU build of PyTorch rather than the exact development build pinned by the original project.

### Frontend

In a second Terminal window:

```bash
cd frontend
npm install
npm run dev
```

The frontend falls back to `http://localhost:8000` for the Flask API when `VITE_FLASK_BACKEND_API_URL` is not defined.

Open the local Vite address shown in Terminal, normally `http://localhost:5173`.

### Optional frontend environment variables

```text
VITE_FLASK_BACKEND_API_URL=http://localhost:8000
VITE_MAX_DIMENSION=1500
```

Both have local defaults in the frontend code.

## Project structure

```text
backend/
  app.py                    Flask API and output endpoints
  depth_map_generator.py    Depth Anything V2 loading/inference
  anaglyph_generator.py     Stereo synthesis and anaglyph rendering
frontend/
  src/ImageUpload.tsx       Upload/depth-map interface
  src/AnaglyphEditor.tsx    3D controls, previews, and downloads
```

Important API endpoints:

- `POST /image` uploads the source image.
- `GET /depth-map` generates and returns the depth visualization.
- `GET /anaglyph` returns the red/cyan output.
- `GET /stereo-pair?mode=parallel` returns the parallel pair.
- `GET /stereo-pair?mode=cross` returns the cross-eyed pair.

## Original implementation details

The original project generates a maximum disparity from the selected strength, maps normalized depth values into pixel shifts, and resolves collisions so nearer pixels take priority. OpenCV inpainting repairs uncovered pixels created by the synthetic viewpoint shift.

For the anaglyph, the standard mode combines the red channel from the left view with the green/blue channels from the right view. The retinal-rivalry option uses optimized matrices based on work by Sanders and McAllister and Eric Dubois to reduce inter-eye color conflict.

## Current status

The repository code now supports all three output formats. The three-format changes have been committed to `master`, but the complete local application still needs runtime validation on the target Intel Mac environment, particularly the local PyTorch installation and Depth Anything V2 checkpoint setup.
