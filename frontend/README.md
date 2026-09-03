# Anaglyph & Friends Frontend

React + TypeScript + Vite frontend for the local **Anaglyph & Friends** 3D technique studio.

The interface accepts one 2D image and works with the Flask backend to provide:

- Red/cyan, parallel, and cross-eyed stereo
- ChromaDepth
- Cardboard / phone-viewer output
- Traditional stereoscope cards with arched image tops and text
- Wiggle-grams
- Random-dot stereograms
- Pattern-based stereograms, including custom uploaded patterns
- Lenticular interlacing and printable calibration bars
- Individual left/right eye downloads
- AI depth-map preview plus 16-bit PNG and float32 depth data

## Conditional technique settings

The quick Red/Cyan, Parallel, and Cross-Eyed modes stay visible at the top of the output area. Additional methods live in the grouped **More techniques** selector.

Technique-specific controls appear only when that mode is selected. Viewer and print techniques open with practical starting presets:

- Google Cardboard-style: 1920×1080, 121 mm screen width, 63 mm lens separation
- Holmes-style stereograph: 7 × 3.5 in card, 300 DPI, arched image tops
- Lenticular: 60 LPI / 600 DPI / 6 views, with 50 LPI and 40 LPI alternatives

Specialized settings are edited first and then committed with **Apply settings**, avoiding repeated expensive rendering while fields are being changed.

## Input

The original source image is retained at full resolution. Images can be loaded by:

- **Choose image**
- drag-and-drop onto the source panel
- **Command-V** paste
- **U** to open the image chooser

The source and depth-map thumbnails can be clicked for larger inspection.

## Keyboard shortcuts

There is deliberately no global regenerate shortcut.

- **R**: red/cyan
- **V**: parallel
- **X**: cross-eyed
- **F**: fullscreen selected technique
- **D**: download selected technique
- **U**: choose image
- **Command-V**: normal macOS image paste

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

See the repository-level `README.md` for model setup, local/offline operation, backend architecture, Intel Mac notes, and the project roadmap.
