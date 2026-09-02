import { useState, useEffect, useRef } from "react";
import "./styles/AnaglyphEditor.css";

type OutputKind = "anaglyph" | "parallel" | "cross";

function AnaglyphEditor({ isDepthMapReady, isChangeAllowed, setIsChangeAllowed}: { isDepthMapReady: boolean, isChangeAllowed: boolean, setIsChangeAllowed: (value: boolean) => void}) {
    const apiUrl = import.meta.env.VITE_FLASK_BACKEND_API_URL || "http://localhost:8000";
    const previewRef = useRef<HTMLDivElement>(null);
    const [activeOutput, setActiveOutput] = useState<OutputKind>("anaglyph");
    const [outputUrls, setOutputUrls] = useState<Record<OutputKind, string | null>>({ anaglyph: null, parallel: null, cross: null });
    const [outputsAreLoading, setOutputsAreLoading] = useState(false);
    const [popOut, setPopOut] = useState(false);
    const [maxDisparityPercentage, setMaxDisparityPercentage] = useState(2);
    const [optimiseRRAnaglyph, setOptimiseRRAnaglyph] = useState(false);
    const [sliderValue, setSliderValue] = useState(2);

    useEffect(() => { if (isDepthMapReady) fetchOutputs(); }, [isDepthMapReady, popOut, maxDisparityPercentage, optimiseRRAnaglyph]);
    useEffect(() => { setIsChangeAllowed(!outputsAreLoading); }, [outputsAreLoading]);

    const fetchBlob = async (url: string) => { const response = await fetch(url, { method: "GET", credentials: "include" }); if (!response.ok) throw new Error(`Request failed with status ${response.status}`); return response.blob(); };
    const fetchOutputs = async () => {
        setOutputsAreLoading(true);
        try {
            const params = `pop_out=${popOut}&max_disparity_percentage=${maxDisparityPercentage}`;
            const [a, p, c] = await Promise.all([
                fetchBlob(`${apiUrl}/anaglyph?${params}&optimised_RR_anaglyph=${optimiseRRAnaglyph}`),
                fetchBlob(`${apiUrl}/stereo-pair?mode=parallel&${params}`),
                fetchBlob(`${apiUrl}/stereo-pair?mode=cross&${params}`),
            ]);
            setOutputUrls((old) => { Object.values(old).forEach((url) => { if (url) URL.revokeObjectURL(url); }); return { anaglyph: URL.createObjectURL(a), parallel: URL.createObjectURL(p), cross: URL.createObjectURL(c) }; });
        } catch (error) { console.error("Failed to fetch 3D outputs", error); } finally { setOutputsAreLoading(false); }
    };

    const handleDownload = () => { const url = outputUrls[activeOutput]; if (!url) return; const names = { anaglyph: "anaglyph.jpeg", parallel: "parallel-stereo.jpeg", cross: "cross-eyed-stereo.jpeg" }; const link = document.createElement("a"); link.href = url; link.download = names[activeOutput]; document.body.appendChild(link); link.click(); link.remove(); };
    const titles = { anaglyph: "Red / Cyan Anaglyph", parallel: "Parallel Stereo", cross: "Cross-Eyed Stereo" };
    const descriptions = { anaglyph: "For red-cyan 3D glasses", parallel: "Left eye on left · relaxed / wall-eyed viewing", cross: "Views swapped for cross-eyed free viewing" };

    return <div className="editorWorkspace">
        <div className="editorHeader"><div><div className="panelLabel">OUTPUT</div><h2>3D Image Generator</h2></div><div className="generationState">{outputsAreLoading ? <><span className="miniLoader" /> Generating</> : isDepthMapReady ? "Ready" : "Waiting for image"}</div></div>
        <div className="outputTabs">{(["anaglyph", "parallel", "cross"] as OutputKind[]).map((kind) => <button key={kind} className={activeOutput === kind ? "outputTab active" : "outputTab"} onClick={() => setActiveOutput(kind)}>{kind === "anaglyph" ? "Anaglyph" : kind === "parallel" ? "Parallel" : "Cross-Eyed"}</button>)}</div>
        <div className="previewFrame" ref={previewRef}>
            {outputUrls[activeOutput] ? <img src={outputUrls[activeOutput]!} alt={titles[activeOutput]} /> : <div className="emptyStage"><div className="stereoGlyph">◉ ◉</div><strong>Your 3D result will appear here</strong><span>Choose an image in the source panel.</span></div>}
            {outputsAreLoading && <div className="loadingVeil"><div className="largeLoader" /><span>Building stereo views…</span></div>}
        </div>
        <div className="previewMeta"><div><strong>{titles[activeOutput]}</strong><span>{descriptions[activeOutput]}</span></div><div className="previewActions"><button onClick={() => previewRef.current?.requestFullscreen?.()} disabled={!outputUrls[activeOutput]}>Fullscreen</button><button className="downloadAction" onClick={handleDownload} disabled={!outputUrls[activeOutput]}>Download JPEG</button></div></div>
        <div className="settingsCard">
            <div className="settingGroup wide"><div className="settingTitle"><span>3D strength</span><strong>{sliderValue.toFixed(1)}%</strong></div><input type="range" min="0" max="6" step="0.1" value={sliderValue} disabled={!isChangeAllowed} onChange={(e) => setSliderValue(parseFloat(e.target.value))} onMouseUp={() => isChangeAllowed && setMaxDisparityPercentage(sliderValue)} onTouchEnd={() => isChangeAllowed && setMaxDisparityPercentage(sliderValue)} /><div className="rangeLabels"><span>Subtle</span><span>Strong</span></div></div>
            <label className="toggleSetting"><span><strong>Pop out</strong><small>Place depth in front of screen</small></span><input type="checkbox" checked={popOut} disabled={!isChangeAllowed} onChange={(e) => setPopOut(e.target.checked)} /></label>
            <label className="toggleSetting"><span><strong>Reduce retinal rivalry</strong><small>Anaglyph output only</small></span><input type="checkbox" checked={optimiseRRAnaglyph} disabled={!isChangeAllowed} onChange={(e) => setOptimiseRRAnaglyph(e.target.checked)} /></label>
        </div>
    </div>;
}
export default AnaglyphEditor;
