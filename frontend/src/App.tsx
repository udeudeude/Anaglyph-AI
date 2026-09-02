import './styles/App.css'
import anaglyphAILogoLight from './assets/anaglyph_ai_pop_in_transparent_light_mode.svg'
import ImageUpload from './ImageUpload.tsx'
import { useState } from 'react'
import AnaglyphEditor from './AnaglyphEditor.tsx'
import Footer from './Footer.tsx'

function App() {
    const [isDepthMapReady, setIsDepthMapReady] = useState<boolean>(false)
    // Prevent changing the source image while depth estimation or 3D output generation is in progress.
    // Initialize to true so the user can upload an image immediately.
    const [isChangeAllowed, setIsChangeAllowed] = useState<boolean>(true)

    return (
        <>
            <div>
                <img src={anaglyphAILogoLight}
                   className="responsive_title"
                   alt="Anaglyph AI Logo"/>
            </div>
            <ImageUpload setIsDepthMapReadyStateLifter={setIsDepthMapReady} isChangeAllowed={isChangeAllowed} setIsChangeAllowed={setIsChangeAllowed}/>
            <AnaglyphEditor isDepthMapReady={isDepthMapReady} isChangeAllowed={isChangeAllowed} setIsChangeAllowed={setIsChangeAllowed}/>
            <Footer />
        </>
  )
}

export default App
