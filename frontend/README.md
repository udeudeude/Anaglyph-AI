# Anaglyph AI Frontend

React + TypeScript + Vite frontend for Anaglyph AI.

The interface accepts a single 2D image, displays the Depth Anything V2 depth-map result, and previews three downloadable stereoscopic outputs produced by the Flask backend:

1. Red/cyan anaglyph
2. Parallel stereo pair
3. Cross-eyed stereo pair

## Development

```bash
npm install
npm run dev
```

By default the frontend talks to the local Flask backend at:

```text
http://localhost:8000
```

You can override that with:

```text
VITE_FLASK_BACKEND_API_URL=<backend URL>
```

Image resizing defaults to a maximum dimension of 1500 pixels and can be overridden with:

```text
VITE_MAX_DIMENSION=<pixels>
```

## Build

```bash
npm run build
```

See the repository-level `README.md` for the complete architecture, backend/model setup, local/offline operation, and output-format details.
