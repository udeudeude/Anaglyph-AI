import './styles/App.css'
import ImageUpload from './ImageUpload.tsx'
import { useState } from 'react'
import AnaglyphEditor from './AnaglyphEditor.tsx'
import Footer from './Footer.tsx'

function App() {
    const [isDepthMapReady, setIsDepthMapReady] = useState<boolean>(false)
    const [isChangeAllowed, setIsChangeAllowed] = useState<boolean>(true)

    return (
        <div className="appShell">
            <header className="topBar">
                <div>
                    <div className="brandEyebrow">LOCAL AI STEREO WORKSPACE</div>
                    <h1 className="brandTitle">Anaglyph AI</h1>
                </div>
                <div className="localBadge"><span className="statusDot" /> Processing locally</div>
            </header>

            <main className="workspace">
                <aside className="controlRail">
                    <ImageUpload
                        setIsDepthMapReadyStateLifter={setIsDepthMapReady}
                        isChangeAllowed={isChangeAllowed}
                        setIsChangeAllowed={setIsChangeAllowed}
                    />
                </aside>

                <section className="stagePanel">
                    <AnaglyphEditor
                        isDepthMapReady={isDepthMapReady}
                        isChangeAllowed={isChangeAllowed}
                        setIsChangeAllowed={setIsChangeAllowed}
                    />
                </section>
            </main>

            <Footer />
        </div>
    )
}

export default App
