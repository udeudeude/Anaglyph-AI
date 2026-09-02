# Anaglyph AI

Anaglyph AI converts a single 2D (monocular) image into three stereoscopic 3D output formats:

1. **Red/cyan anaglyph** for red-cyan glasses.
2. **Parallel stereo pair** (left-eye image on the left, right-eye image on the right) for relaxed/wall-eyed free viewing.
3. **Cross-eyed stereo pair** (right-eye image on the left, left-eye image on the right) for cross-eyed free viewing.

The project uses **Depth Anything V2** to estimate a depth map from the source image, then synthesizes left- and right-eye views from that depth data. The three output formats are different presentations of the same generated stereo pair.

The original project and hosted demonstration were created by **Duy Huynh**. The original hosted version is at [anaglyph-ai.com](https://anaglyph-ai.com). This repository version extends the original project with parallel/cross-eyed output and a redesigned local-first stereo workspace.

## Interface

The current frontend uses a dark desktop workspace designed for local image processing:

- a persistent **Source** sidebar with image upload and AI depth-map preview;
- a large central output stage;
- tabs for **Anaglyph**, **Parallel**, and **Cross-Eyed** viewing;
- instant switching between the three generated outputs;
- **Fullscreen** and **Download JPEG** controls for the selected output;
- shared **3D Strength** and **Pop Out** controls;
- **Reduce Retinal Rivalry** for the anaglyph output;
- a visible local-processing indicator.

The processing pipeline is:

`single 2D image -> Depth Anything V2 depth map -> synthetic left/right views -> chosen 3D output`

## Output formats

### Red/cyan anaglyph
The left and right stereo views are combined into color channels so each eye receives a different view through red-cyan glasses. The optional retinal-rivalry reduction uses optimized color matrices based on the Dubois approach.

### Parallel stereo
The output is a single side-by-side JPEG arranged `LEFT EYE | RIGHT EYE`, intended for parallel (wall-eyed) free viewing.

### Cross-eyed stereo
The same stereo pair is saved as `RIGHT EYE | LEFT EYE`, intended for cross-eyed free viewing.

## How the 3D conversion works

### 1. Depth estimation
The backend uses [Depth Anything V2](https://github.com/DepthAnything/Depth-Anything-V2), an open-source monocular depth-estimation model. The current code loads the **ViT-S (`vits`)** model.

At runtime PyTorch chooses CUDA when available, then Apple MPS when supported, and otherwise CPU. An Intel Mac therefore uses the CPU path.

### 2. Stereo image synthesis
The normalized depth map is converted into horizontal pixel shifts. Near and far pixels receive different shifts, producing synthetic left-eye and right-eye views. A single photograph cannot contain surfaces hidden behind foreground objects, so shifting pixels creates holes near depth discontinuities. The project fills those holes with OpenCV's Telea inpainting method.

### 3. Output rendering
The left/right views are either merged into a red/cyan anaglyph, concatenated left-to-right for parallel viewing, or concatenated in reversed order for cross-eyed viewing.

## Local and offline use

Once the dependencies, Depth Anything V2 source, and model checkpoint are installed, image processing does **not** require an Internet connection.

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

The original requirements pin a development PyTorch build that may not exist for older Intel Macs. The tested 2015 Intel Mac setup used **Python 3.10.4, PyTorch 2.2.2, torchvision 0.17.2, and NumPy 1.26.4**. The Flask backend defaults to `http://localhost:8000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend defaults to `http://localhost:8000` for the Flask API and a 1500-pixel maximum source dimension when environment variables are not defined. Vite normally serves the interface at `http://localhost:5173`.

## Project structure

```text
backend/
  app.py                    Flask API and output endpoints
  depth_map_generator.py    Depth Anything V2 loading/inference
  anaglyph_generator.py     Stereo synthesis and anaglyph rendering
frontend/
  src/App.tsx               Application shell
  src/ImageUpload.tsx       Source/depth sidebar
  src/AnaglyphEditor.tsx    Tabbed 3D workspace, controls and downloads
```

Important API endpoints:

- `POST /image` uploads the source image.
- `GET /depth-map` generates and returns the depth visualization.
- `GET /anaglyph` returns the red/cyan output.
- `GET /stereo-pair?mode=parallel` returns the parallel pair.
- `GET /stereo-pair?mode=cross` returns the cross-eyed pair.

## Current status

The three output formats and redesigned local interface are committed to `master`. The underlying local processing pipeline has been successfully run on a 2015 Intel MacBook Pro; the redesigned frontend should be re-tested after pulling the latest repository changes.
