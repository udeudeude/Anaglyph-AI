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

// Technique-setting sliders are deliberately staged so the user can move them
// freely and then choose Apply settings. Discrete controls should feel immediate:
// selects, checkboxes, number/text fields (on change/blur), and ordinary buttons
// automatically press the panel's Apply button after React has committed the new
// draft state. Event delegation also covers the duplicate controls shown in the
// fullscreen dock without adding a second behavior path.
const scheduleTechniqueAutoApply = (target: EventTarget | null) => {
  const element = target instanceof Element ? target : null
  const panel = element?.closest('.techniqueSettings')
  if (!panel) return
  if (element?.matches('input[type="range"]')) return
  if (element?.closest('.applyTechnique')) return

  window.setTimeout(() => {
    const button = panel.querySelector<HTMLButtonElement>('.applyTechnique')
    if (button && !button.disabled) button.click()
  }, 0)
}

document.addEventListener('change', (event) => scheduleTechniqueAutoApply(event.target))
document.addEventListener('click', (event) => {
  const element = event.target instanceof Element ? event.target : null
  if (!element?.closest('.techniqueSettings button')) return
  scheduleTechniqueAutoApply(event.target)
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
