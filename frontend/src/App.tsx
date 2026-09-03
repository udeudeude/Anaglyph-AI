import './styles/App.css'
import ImageUpload from './ImageUpload.tsx'
import { useEffect, useState } from 'react'
import type { CSSProperties, MouseEvent as ReactMouseEvent } from 'react'
import AnaglyphEditor from './AnaglyphEditor.tsx'

type ProcessingStage = 'idle' | 'uploading' | 'depth' | 'stereo' | 'technique' | 'full' | 'ready' | 'error'

const stageLabels: Record<ProcessingStage, string> = {
    idle: 'Processing locally',
    uploading: 'Loading original…',
    depth: 'Estimating depth…',
    stereo: 'Building stereo views…',
    technique: 'Rendering selected technique…',
    full: 'Rendering full resolution…',
    ready: 'Ready · processing locally',
    error: 'Processing error',
}

function App() {
    const [isDepthMapReady, setIsDepthMapReady] = useState<boolean>(false)
    const [isChangeAllowed, setIsChangeAllowed] = useState<boolean>(true)
    const [processingStage, setProcessingStage] = useState<ProcessingStage>('idle')
    const [sidebarWidth, setSidebarWidth] = useState<number>(() => Number(localStorage.getItem('aaf-sidebar-width')) || 280)
    const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(() => localStorage.getItem('aaf-sidebar-collapsed') === 'true')

    useEffect(() => {
        localStorage.setItem('aaf-sidebar-collapsed', String(sidebarCollapsed))
    }, [sidebarCollapsed])

    const beginResize = (event: ReactMouseEvent<HTMLDivElement>) => {
        if (sidebarCollapsed) return
        event.preventDefault()
        const startX = event.clientX
        const startWidth = sidebarWidth
        const move = (moveEvent: MouseEvent) => {
            const next = Math.max(220, Math.min(430, startWidth + moveEvent.clientX - startX))
            setSidebarWidth(next)
            localStorage.setItem('aaf-sidebar-width', String(next))
        }
        const stop = () => {
            document.removeEventListener('mousemove', move)
            document.removeEventListener('mouseup', stop)
            document.body.classList.remove('resizingRail')
        }
        document.body.classList.add('resizingRail')
        document.addEventListener('mousemove', move)
        document.addEventListener('mouseup', stop)
    }

    const workspaceStyle = { '--sidebar-width': `${sidebarWidth}px` } as CSSProperties

    return (
        <div className="appShell">
            <header className="topBar">
                <div>
                    <div className="brandEyebrow">LOCAL AI STEREO WORKSPACE</div>
                    <h1 className="brandTitle">Anaglyph &amp; Friends</h1>
                </div>
                <div className={`localBadge stage-${processingStage}`}>
                    <span className="statusDot" /> {stageLabels[processingStage]}
                </div>
            </header>

            <main className={`workspace ${sidebarCollapsed ? 'railCollapsed' : ''}`} style={workspaceStyle}>
                <aside className="controlRail">
                    <button className="collapseRail" onClick={() => setSidebarCollapsed(true)} title="Collapse source panel" aria-label="Collapse source panel">‹</button>
                    <ImageUpload
                        setIsDepthMapReadyStateLifter={setIsDepthMapReady}
                        isChangeAllowed={isChangeAllowed}
                        setIsChangeAllowed={setIsChangeAllowed}
                        setProcessingStage={setProcessingStage}
                    />
                </aside>

                <div className="railResizer" onMouseDown={beginResize} title="Drag to resize source panel" />

                <section className="stagePanel">
                    {sidebarCollapsed && <button className="expandRail" onClick={() => setSidebarCollapsed(false)} title="Show source panel">› Source</button>}
                    <AnaglyphEditor
                        isDepthMapReady={isDepthMapReady}
                        isChangeAllowed={isChangeAllowed}
                        setIsChangeAllowed={setIsChangeAllowed}
                        setProcessingStage={setProcessingStage}
                    />
                </section>
            </main>
        </div>
    )
}

export default App
