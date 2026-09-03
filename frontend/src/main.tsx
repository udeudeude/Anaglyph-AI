import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/index.css'
import App from './App.tsx'

// Seed sane defaults before the editor mounts. An earlier settings reader treated
// a missing localStorage value as Number(null) === 0, which could make the first
// rendered stereo image invisible by setting its on-screen size to 0%.
const settingsSchemaVersion = '2'
if (localStorage.getItem('aaf-settings-schema') !== settingsSchemaVersion) {
  const strength = localStorage.getItem('aaf-strength')
  const viewScale = localStorage.getItem('aaf-view-scale')
  const jpegQuality = localStorage.getItem('aaf-jpeg-quality')

  if (strength === null || Number(strength) === 0) localStorage.setItem('aaf-strength', '2')
  if (viewScale === null || Number(viewScale) < 35) localStorage.setItem('aaf-view-scale', '100')
  if (jpegQuality === null || Number(jpegQuality) < 70) localStorage.setItem('aaf-jpeg-quality', '95')

  localStorage.setItem('aaf-settings-schema', settingsSchemaVersion)
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
