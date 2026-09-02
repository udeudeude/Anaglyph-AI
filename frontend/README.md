# Anaglyph & Friends Frontend

React + TypeScript + Vite frontend for the local **Anaglyph & Friends** stereo workspace.

The interface accepts a single 2D image and works with the Flask backend to provide:

1. Red/cyan anaglyph
2. Parallel stereo pair
3. Cross-eyed stereo pair
4. Individual left-eye and right-eye downloads
5. AI depth-map preview plus downloadable 16-bit PNG and float32 depth data

## Input

The original source image is uploaded without the old 1500-pixel frontend downscale. Images can be loaded by:

- **Choose image**
- dragging and dropping an image onto the source panel
- pasting an image with **Command-V**
- pressing **U** to open the image chooser

The source image and depth-map thumbnails can be clicked for a larger inspection view.

## Stereo viewer

The application keeps a lightweight preview render separate from full-resolution downloadable output. Changing stereo strength or Pop Out regenerates the preview pair once; red/cyan, parallel, and cross-eyed previews are then derived from that cached pair.

Keyboard shortcuts deliberately do not include any global regenerate command:

- **R**: red/cyan anaglyph
- **V**: parallel view
- **X**: cross-eyed view
- **F**: fullscreen selected output
- **D**: download selected output at full source resolution
- **U**: choose a new source image

Viewer controls include independent on-screen pair size, zoom/pan, fullscreen, and persistent settings stored locally in the browser.

## Full-resolution downloads

JPEG and PNG are available. JPEG quality is adjustable. The first full-resolution download after changing stereo geometry may take longer because the backend creates and caches a full-resolution left/right pair. Subsequent output formats reuse that pair.

## Development

```bash
npm install
npm run dev
```

By default the frontend talks to:

```text
http://localhost:8000
```

Override it with:

```text
VITE_FLASK_BACKEND_API_URL=<backend URL>
```

## Build

```bash
npm run build
```

See the repository-level `README.md` for model setup, local/offline operation, backend architecture, and Intel Mac notes.
