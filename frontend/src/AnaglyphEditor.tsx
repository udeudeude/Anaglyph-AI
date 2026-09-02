import { useEffect, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import "./styles/AnaglyphEditor.css";

type OutputKind = "anaglyph" | "parallel" | "cross";
type DownloadKind = OutputKind | "left" | "right";
type ProcessingStage = 'idle' | 'uploading' | 'depth' | 'stereo' | 'full' | 'ready' | 'error';

type Props = {
    isDepthMapReady: boolean;
    isChangeAllowed: boolean;
    setIsChangeAllowed: (value: boolean) => void;
    setProcessingStage: (stage: ProcessingStage) => void;
};

const readNumber = (key: string, fallback: number) => {
    const value = Number(localStorage.getItem(key));
    return Number.isFinite(value) ? value : fallback;
};

function AnaglyphEditor({ isDepthMapReady, isChangeAllowed, setIsChangeAllowed, setProcessingStage }: Props) {
    const apiUrl = import.meta.env.VITE_FLASK_BACKEND_API_URL || "http://localhost:8000";
    const previewRef = useRef<HTMLDivElement>(null);
    const dragRef = useRef<{x: number; y: number; panX: number; panY: number} | null>(null);

    const [activeOutput, setActiveOutput] = useState<OutputKind>(() => {
        const saved = localStorage.getItem('aaf-output');
        return saved === 'parallel' || saved === 'cross' ? saved : 'anaglyph';
    });
    const [outputUrls, setOutputUrls] = useState<Record<OutputKind, string | null>>({ anaglyph: null, parallel: null, cross: null });
    const [outputsAreLoading, setOutputsAreLoading] = useState(false);
    const [fullPreparing, setFullPreparing] = useState(false);
    const [hasRendered, setHasRendered] = useState(false);
    const [popOut, setPopOut] = useState(() => localStorage.getItem('aaf-pop-out') === 'true');
    const [appliedStrength, setAppliedStrength] = useState(() => readNumber('aaf-strength', 2));
    const [sliderValue, setSliderValue] = useState(() => readNumber('aaf-strength', 2));
    const [optimiseRRAnaglyph, setOptimiseRRAnaglyph] = useState(() => localStorage.getItem('aaf-retinal-rivalry') === 'true');
    const [viewScale, setViewScale] = useState(() => readNumber('aaf-view-scale', 100));
    const [downloadFormat, setDownloadFormat] = useState<'jpeg' | 'png'>(() => localStorage.getItem('aaf-download-format') === 'png' ? 'png' : 'jpeg');
    const [jpegQuality, setJpegQuality] = useState(() => readNumber('aaf-jpeg-quality', 95));
    const [zoom, setZoom] = useState(1);
    const [pan, setPan] = useState({x: 0, y: 0});

    const renderParams = () => `pop_out=${popOut}&max_disparity_percentage=${appliedStrength}`;
    const previewUrl = (kind: OutputKind) => `${apiUrl}/output/${kind}?scope=preview&format=jpeg&quality=90&${renderParams()}&optimised_RR_anaglyph=${optimiseRRAnaglyph}`;

    const revokeUrls = (urls: Record<OutputKind, string | null>) => {
        Object.values(urls).forEach(url => { if (url) URL.revokeObjectURL(url); });
    };

    const fetchPreviewBlob = async (kind: OutputKind) => {
        const response = await fetch(previewUrl(kind), { method: "GET", credentials: "include" });
        if (!response.ok) throw new Error(`Preview request failed with status ${response.status}`);
        return response.blob();
    };

    const renderPreview = async () => {
        if (!isDepthMapReady) return;
        setOutputsAreLoading(true);
        setIsChangeAllowed(false);
        setProcessingStage('stereo');
        try {
            const renderResponse = await fetch(`${apiUrl}/render?${renderParams()}`, { method: "GET", credentials: "include" });
            if (!renderResponse.ok) throw new Error(`Stereo render failed with status ${renderResponse.status}`);
            const [anaglyphBlob, parallelBlob, crossBlob] = await Promise.all([
                fetchPreviewBlob('anaglyph'), fetchPreviewBlob('parallel'), fetchPreviewBlob('cross')
            ]);
            setOutputUrls(old => {
                revokeUrls(old);
                return {
                    anaglyph: URL.createObjectURL(anaglyphBlob),
                    parallel: URL.createObjectURL(parallelBlob),
                    cross: URL.createObjectURL(crossBlob),
                };
            });
            setHasRendered(true);
            setProcessingStage('ready');
        } catch (error) {
            console.error("Failed to render stereo preview", error);
            setProcessingStage('error');
        } finally {
            setOutputsAreLoading(false);
            setIsChangeAllowed(true);
        }
    };

    const refreshAnaglyphOnly = async () => {
        if (!hasRendered) return;
        setOutputsAreLoading(true);
        try {
            const blob = await fetchPreviewBlob('anaglyph');
            setOutputUrls(old => {
                if (old.anaglyph) URL.revokeObjectURL(old.anaglyph);
                return {...old, anaglyph: URL.createObjectURL(blob)};
            });
        } catch (error) {
            console.error("Failed to update anaglyph preview", error);
        } finally {
            setOutputsAreLoading(false);
        }
    };

    useEffect(() => { if (isDepthMapReady) void renderPreview(); }, [isDepthMapReady, popOut, appliedStrength]);
    useEffect(() => { if (hasRendered) void refreshAnaglyphOnly(); }, [optimiseRRAnaglyph]);
    useEffect(() => {
        if (!isDepthMapReady) {
            setHasRendered(false);
            setOutputUrls(old => { revokeUrls(old); return {anaglyph: null, parallel: null, cross: null}; });
        }
    }, [isDepthMapReady]);

    useEffect(() => { localStorage.setItem('aaf-output', activeOutput); setZoom(1); setPan({x: 0, y: 0}); }, [activeOutput]);
    useEffect(() => { localStorage.setItem('aaf-pop-out', String(popOut)); }, [popOut]);
    useEffect(() => { localStorage.setItem('aaf-strength', String(appliedStrength)); }, [appliedStrength]);
    useEffect(() => { localStorage.setItem('aaf-retinal-rivalry', String(optimiseRRAnaglyph)); }, [optimiseRRAnaglyph]);
    useEffect(() => { localStorage.setItem('aaf-view-scale', String(viewScale)); }, [viewScale]);
    useEffect(() => { localStorage.setItem('aaf-download-format', downloadFormat); }, [downloadFormat]);
    useEffect(() => { localStorage.setItem('aaf-jpeg-quality', String(jpegQuality)); }, [jpegQuality]);

    const fullscreen = () => previewRef.current?.requestFullscreen?.();

    const downloadKind = async (kind: DownloadKind) => {
        if (!isDepthMapReady || fullPreparing) return;
        setFullPreparing(true);
        setIsChangeAllowed(false);
        setProcessingStage('full');
        try {
            const prepare = await fetch(`${apiUrl}/prepare-full?${renderParams()}`, { method: 'GET', credentials: 'include' });
            if (!prepare.ok) throw new Error(`Full-resolution render failed with status ${prepare.status}`);
            const params = new URLSearchParams({
                scope: 'full',
                format: downloadFormat,
                quality: String(jpegQuality),
                download: 'true',
                pop_out: String(popOut),
                max_disparity_percentage: String(appliedStrength),
                optimised_RR_anaglyph: String(optimiseRRAnaglyph),
            });
            const link = document.createElement('a');
            link.href = `${apiUrl}/output/${kind}?${params.toString()}`;
            document.body.appendChild(link);
            link.click();
            link.remove();
            setProcessingStage('ready');
        } catch (error) {
            console.error("Failed to prepare full-resolution download", error);
            setProcessingStage('error');
        } finally {
            setFullPreparing(false);
            setIsChangeAllowed(true);
        }
    };

    useEffect(() => {
        const onKeyDown = (event: KeyboardEvent) => {
            if (event.metaKey || event.ctrlKey || event.altKey || event.shiftKey || event.repeat) return;
            const target = event.target as HTMLElement | null;
            if (target && (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName))) return;
            const key = event.key.toLowerCase();
            if (key === 'r') { event.preventDefault(); setActiveOutput('anaglyph'); }
            else if (key === 'v') { event.preventDefault(); setActiveOutput('parallel'); }
            else if (key === 'x') { event.preventDefault(); setActiveOutput('cross'); }
            else if (key === 'f' && outputUrls[activeOutput]) { event.preventDefault(); fullscreen(); }
            else if (key === 'd' && outputUrls[activeOutput]) { event.preventDefault(); void downloadKind(activeOutput); }
        };
        window.addEventListener('keydown', onKeyDown);
        return () => window.removeEventListener('keydown', onKeyDown);
    }, [activeOutput, outputUrls, isDepthMapReady, fullPreparing, downloadFormat, jpegQuality, popOut, appliedStrength, optimiseRRAnaglyph]);

    const zoomBy = (amount: number) => {
        const next = Math.max(1, Math.min(4, Number((zoom + amount).toFixed(2))));
        setZoom(next);
        if (next === 1) setPan({x: 0, y: 0});
    };
    const resetZoom = () => { setZoom(1); setPan({x: 0, y: 0}); };
    const beginPan = (event: ReactPointerEvent<HTMLDivElement>) => {
        if (zoom <= 1) return;
        dragRef.current = {x: event.clientX, y: event.clientY, panX: pan.x, panY: pan.y};
        event.currentTarget.setPointerCapture(event.pointerId);
    };
    const movePan = (event: ReactPointerEvent<HTMLDivElement>) => {
        if (!dragRef.current) return;
        setPan({x: dragRef.current.panX + event.clientX - dragRef.current.x, y: dragRef.current.panY + event.clientY - dragRef.current.y});
    };
    const endPan = () => { dragRef.current = null; };

    const titles = { anaglyph: "Red / Cyan Anaglyph", parallel: "Parallel Stereo", cross: "Cross-Eyed Stereo" };
    const descriptions = { anaglyph: "For red-cyan 3D glasses", parallel: "Left eye on left · relaxed / wall-eyed viewing", cross: "Views swapped for cross-eyed free viewing" };

    return (
        <div className="editorWorkspace">
            <div className="editorHeader">
                <div><div className="panelLabel">OUTPUT</div><h2>3D Image Generator</h2></div>
                <div className="generationState">{fullPreparing ? <><span className="miniLoader" /> Full resolution</> : outputsAreLoading ? <><span className="miniLoader" /> Generating preview</> : isDepthMapReady ? "Ready" : "Waiting for image"}</div>
            </div>

            <div className="outputTabs">
                <button className={activeOutput === 'anaglyph' ? 'outputTab active' : 'outputTab'} onClick={() => setActiveOutput('anaglyph')}>Red/Cyan <kbd>R</kbd></button>
                <button className={activeOutput === 'parallel' ? 'outputTab active' : 'outputTab'} onClick={() => setActiveOutput('parallel')}>Parallel <kbd>V</kbd></button>
                <button className={activeOutput === 'cross' ? 'outputTab active' : 'outputTab'} onClick={() => setActiveOutput('cross')}>Cross-Eyed <kbd>X</kbd></button>
            </div>

            <div className={`previewFrame ${zoom > 1 ? 'zoomed' : ''}`} ref={previewRef} onPointerDown={beginPan} onPointerMove={movePan} onPointerUp={endPan} onPointerCancel={endPan} onDoubleClick={resetZoom}>
                {outputUrls[activeOutput] ? <img src={outputUrls[activeOutput]!} alt={titles[activeOutput]} draggable={false} style={{maxWidth: `${viewScale}%`, transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`}} /> : (
                    <div className="emptyStage"><div className="stereoGlyph">◉ ◉</div><strong>Your 3D result will appear here</strong><span>Drop, choose, or paste an image in the source panel.</span></div>
                )}
                {outputsAreLoading && <div className="loadingVeil"><div className="largeLoader" /><span>Building stereo views…</span></div>}
            </div>

            <div className="previewMeta">
                <div><strong>{titles[activeOutput]}</strong><span>{descriptions[activeOutput]}</span></div>
                <div className="previewActions">
                    <div className="zoomControls" aria-label="Preview zoom"><button onClick={() => zoomBy(-0.25)} disabled={zoom <= 1}>−</button><button onClick={resetZoom}>{Math.round(zoom * 100)}%</button><button onClick={() => zoomBy(0.25)} disabled={zoom >= 4}>＋</button></div>
                    <button onClick={fullscreen} disabled={!outputUrls[activeOutput]}>Fullscreen <kbd>F</kbd></button>
                    <button className="downloadAction" onClick={() => void downloadKind(activeOutput)} disabled={!outputUrls[activeOutput] || fullPreparing}>Download <kbd>D</kbd></button>
                </div>
            </div>

            <div className="settingsCard">
                <div className="settingGroup">
                    <div className="settingTitle"><span>3D strength</span><strong>{sliderValue.toFixed(1)}%</strong></div>
                    <input type="range" min="0" max="6" step="0.1" value={sliderValue} disabled={!isChangeAllowed} onChange={(e) => setSliderValue(parseFloat(e.target.value))} onPointerUp={() => isChangeAllowed && setAppliedStrength(sliderValue)} onKeyUp={() => isChangeAllowed && setAppliedStrength(sliderValue)} />
                    <div className="rangeLabels"><span>Subtle</span><span>{sliderValue !== appliedStrength ? 'Release to apply' : 'Strong'}</span></div>
                </div>

                <div className="settingGroup">
                    <div className="settingTitle"><span>On-screen pair size</span><strong>{viewScale}%</strong></div>
                    <input type="range" min="35" max="100" step="1" value={viewScale} onChange={(e) => setViewScale(parseInt(e.target.value))} />
                    <div className="rangeLabels"><span>Easier free-viewing</span><span>Fill stage</span></div>
                </div>

                <label className="toggleSetting"><span><strong>Pop out</strong><small>Place depth in front of screen</small></span><input type="checkbox" checked={popOut} disabled={!isChangeAllowed} onChange={(e) => setPopOut(e.target.checked)} /></label>
                <label className="toggleSetting"><span><strong>Reduce retinal rivalry</strong><small>Red/cyan output only</small></span><input type="checkbox" checked={optimiseRRAnaglyph} disabled={!isChangeAllowed} onChange={(e) => setOptimiseRRAnaglyph(e.target.checked)} /></label>
            </div>

            <div className="downloadPanel">
                <div className="downloadHeading"><div><strong>Full-resolution downloads</strong><span>The original pixel dimensions are retained. The first download after changing stereo settings may take longer.</span></div><span className="fullResBadge">FULL RES</span></div>
                <div className="downloadControls">
                    <label>Format<select value={downloadFormat} onChange={(e) => setDownloadFormat(e.target.value as 'jpeg' | 'png')}><option value="jpeg">JPEG</option><option value="png">PNG</option></select></label>
                    {downloadFormat === 'jpeg' && <label>JPEG quality<input type="range" min="70" max="100" step="1" value={jpegQuality} onChange={(e) => setJpegQuality(parseInt(e.target.value))} /><strong>{jpegQuality}</strong></label>}
                    <div className="eyeDownloads"><button onClick={() => void downloadKind('left')} disabled={!hasRendered || fullPreparing}>Left eye</button><button onClick={() => void downloadKind('right')} disabled={!hasRendered || fullPreparing}>Right eye</button></div>
                </div>
            </div>
        </div>
    );
}

export default AnaglyphEditor;
