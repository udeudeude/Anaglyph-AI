import { useEffect, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import "./styles/AnaglyphEditor.css";
import TechniqueControls from './TechniqueControls';
import {
    mergeStoredSettings,
    stereoBasedTechniques,
    techniqueInfo,
    type TechniqueId,
    type TechniqueSettings,
} from './techniques';

type ProcessingStage = 'idle' | 'uploading' | 'depth' | 'stereo' | 'technique' | 'full' | 'ready' | 'error';

type Props = {
    isDepthMapReady: boolean;
    isChangeAllowed: boolean;
    setIsChangeAllowed: (value: boolean) => void;
    setProcessingStage: (stage: ProcessingStage) => void;
};

const allTechniques = new Set<TechniqueId>(['anaglyph', 'parallel', 'cross', 'chromadepth', 'cardboard', 'stereoscope', 'wiggle', 'randomdot', 'pattern', 'lenticular']);
const basicTechniques = new Set<TechniqueId>(['anaglyph', 'parallel', 'cross']);

const readNumber = (key: string, fallback: number) => {
    const raw = localStorage.getItem(key);
    if (raw === null || raw.trim() === '') return fallback;
    const value = Number(raw);
    return Number.isFinite(value) ? value : fallback;
};

const cloneSettings = (settings: TechniqueSettings): TechniqueSettings => JSON.parse(JSON.stringify(settings));

function AnaglyphEditor({ isDepthMapReady, isChangeAllowed, setIsChangeAllowed, setProcessingStage }: Props) {
    const apiUrl = import.meta.env.VITE_FLASK_BACKEND_API_URL || "http://localhost:8000";
    const previewRef = useRef<HTMLDivElement>(null);
    const dragRef = useRef<{x: number; y: number; panX: number; panY: number} | null>(null);

    const [activeTechnique, setActiveTechnique] = useState<TechniqueId>(() => {
        const saved = localStorage.getItem('aaf-technique') as TechniqueId | null;
        return saved && allTechniques.has(saved) ? saved : 'anaglyph';
    });
    const initialSettings = mergeStoredSettings(localStorage.getItem('aaf-technique-settings'));
    const [draftSettings, setDraftSettings] = useState<TechniqueSettings>(() => cloneSettings(initialSettings));
    const [appliedSettings, setAppliedSettings] = useState<TechniqueSettings>(() => cloneSettings(initialSettings));
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
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

    const techniqueDirty = JSON.stringify(draftSettings) !== JSON.stringify(appliedSettings);
    const renderParams = () => `pop_out=${popOut}&max_disparity_percentage=${appliedStrength}`;

    const specialUrl = (technique: TechniqueId, scope: 'preview' | 'full') => {
        const base: Record<string, string> = {
            scope,
            pop_out: String(popOut),
            max_disparity_percentage: String(appliedStrength),
            format: downloadFormat,
            quality: String(jpegQuality),
        };
        if (technique === 'chromadepth') {
            const s = appliedSettings.chromadepth;
            return `${apiUrl}/special/chromadepth?${new URLSearchParams({...base, color_strength: String(s.colorStrength), reverse: String(s.reverse)}).toString()}`;
        }
        if (technique === 'cardboard') {
            const s = appliedSettings.cardboard;
            return `${apiUrl}/special/cardboard?${new URLSearchParams({...base, width: String(s.width), height: String(s.height), screen_width_mm: String(s.screenWidthMm), lens_separation_mm: String(s.lensSeparationMm), image_scale: String(s.imageScale)}).toString()}`;
        }
        if (technique === 'stereoscope') {
            const s = appliedSettings.stereoscope;
            return `${apiUrl}/special/stereoscope?${new URLSearchParams({...base, dpi: String(s.dpi), card_width: String(s.cardWidth), card_height: String(s.cardHeight), image_width: String(s.imageWidth), image_height: String(s.imageHeight), gap: String(s.gap), arch: String(s.arch), title: s.title, caption: s.caption, publisher: s.publisher, card_tone: s.cardTone}).toString()}`;
        }
        if (technique === 'wiggle') {
            const s = appliedSettings.wiggle;
            return `${apiUrl}/special/wiggle?${new URLSearchParams({...base, frames: String(s.frames), duration: String(s.duration)}).toString()}`;
        }
        if (technique === 'randomdot' || technique === 'pattern') {
            const s = appliedSettings.autostereogram;
            return `${apiUrl}/special/autostereogram?${new URLSearchParams({...base, style: technique === 'pattern' ? 'pattern' : 'random', separation: String(s.separation), depth_strength: String(s.depthStrength), dot_size: String(s.dotSize), viewing: s.viewing, color: String(s.color)}).toString()}`;
        }
        if (technique === 'lenticular') {
            const s = appliedSettings.lenticular;
            return `${apiUrl}/special/lenticular?${new URLSearchParams({...base, dpi: String(s.dpi), lpi: String(s.lpi), width_in: String(s.widthIn), height_in: String(s.heightIn), views: String(s.views), slant: String(s.slant)}).toString()}`;
        }
        throw new Error(`No special renderer for ${technique}`);
    };

    const basicUrl = (technique: TechniqueId, scope: 'preview' | 'full') => {
        const params = new URLSearchParams({
            scope,
            format: downloadFormat,
            quality: String(jpegQuality),
            pop_out: String(popOut),
            max_disparity_percentage: String(appliedStrength),
            optimised_RR_anaglyph: String(optimiseRRAnaglyph),
        });
        return `${apiUrl}/output/${technique}?${params.toString()}`;
    };

    const renderActivePreview = async () => {
        if (!isDepthMapReady) return;
        setOutputsAreLoading(true);
        setIsChangeAllowed(false);
        setProcessingStage(basicTechniques.has(activeTechnique) ? 'stereo' : 'technique');
        try {
            let url: string;
            if (basicTechniques.has(activeTechnique)) {
                const renderResponse = await fetch(`${apiUrl}/render?${renderParams()}`, { method: 'GET', credentials: 'include' });
                if (!renderResponse.ok) throw new Error(`Stereo render failed with status ${renderResponse.status}`);
                url = basicUrl(activeTechnique, 'preview');
            } else {
                url = specialUrl(activeTechnique, 'preview');
            }
            const response = await fetch(url, { method: 'GET', credentials: 'include' });
            if (!response.ok) throw new Error(`Technique preview failed with status ${response.status}`);
            const blob = await response.blob();
            const nextUrl = URL.createObjectURL(blob);
            setPreviewUrl(old => { if (old) URL.revokeObjectURL(old); return nextUrl; });
            setHasRendered(true);
            setProcessingStage('ready');
        } catch (error) {
            console.error('Failed to render selected technique', error);
            setProcessingStage('error');
        } finally {
            setOutputsAreLoading(false);
            setIsChangeAllowed(true);
        }
    };

    useEffect(() => { if (isDepthMapReady) void renderActivePreview(); }, [isDepthMapReady, activeTechnique, popOut, appliedStrength, optimiseRRAnaglyph, appliedSettings]);
    useEffect(() => {
        if (!isDepthMapReady) {
            setHasRendered(false);
            setPreviewUrl(old => { if (old) URL.revokeObjectURL(old); return null; });
        }
    }, [isDepthMapReady]);

    useEffect(() => { localStorage.setItem('aaf-technique', activeTechnique); setZoom(1); setPan({x: 0, y: 0}); }, [activeTechnique]);
    useEffect(() => { localStorage.setItem('aaf-pop-out', String(popOut)); }, [popOut]);
    useEffect(() => { localStorage.setItem('aaf-strength', String(appliedStrength)); }, [appliedStrength]);
    useEffect(() => { localStorage.setItem('aaf-retinal-rivalry', String(optimiseRRAnaglyph)); }, [optimiseRRAnaglyph]);
    useEffect(() => { localStorage.setItem('aaf-view-scale', String(viewScale)); }, [viewScale]);
    useEffect(() => { localStorage.setItem('aaf-download-format', downloadFormat); }, [downloadFormat]);
    useEffect(() => { localStorage.setItem('aaf-jpeg-quality', String(jpegQuality)); }, [jpegQuality]);
    useEffect(() => { localStorage.setItem('aaf-technique-settings', JSON.stringify(draftSettings)); }, [draftSettings]);

    const applyTechniqueSettings = () => setAppliedSettings(cloneSettings(draftSettings));
    const fullscreen = () => previewRef.current?.requestFullscreen?.();

    const triggerBlobDownload = (blob: Blob, filename: string) => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    };

    const currentFilename = () => {
        const ext = activeTechnique === 'wiggle' ? 'gif' : (activeTechnique === 'stereoscope' || activeTechnique === 'lenticular' ? 'png' : downloadFormat === 'png' ? 'png' : 'jpg');
        const names: Record<TechniqueId, string> = {
            anaglyph: 'red-cyan-anaglyph', parallel: 'parallel-stereo', cross: 'cross-eyed-stereo', chromadepth: 'chromadepth',
            cardboard: 'cardboard-stereo', stereoscope: 'stereoscope-card', wiggle: 'wiggle-gram', randomdot: 'random-dot-stereogram',
            pattern: 'pattern-stereogram', lenticular: 'lenticular-interlaced',
        };
        return `${names[activeTechnique]}.${ext}`;
    };

    const downloadCurrent = async () => {
        if (!isDepthMapReady || fullPreparing) return;
        setFullPreparing(true);
        setIsChangeAllowed(false);
        setProcessingStage('full');
        try {
            let url: string;
            if (basicTechniques.has(activeTechnique)) {
                const prepare = await fetch(`${apiUrl}/prepare-full?${renderParams()}`, { method: 'GET', credentials: 'include' });
                if (!prepare.ok) throw new Error(`Full-resolution stereo render failed: ${prepare.status}`);
                url = basicUrl(activeTechnique, 'full');
            } else {
                url = specialUrl(activeTechnique, 'full');
            }
            const response = await fetch(url, { method: 'GET', credentials: 'include' });
            if (!response.ok) throw new Error(`Full-resolution output failed: ${response.status}`);
            triggerBlobDownload(await response.blob(), currentFilename());
            setProcessingStage('ready');
        } catch (error) {
            console.error('Failed to create full-resolution download', error);
            setProcessingStage('error');
        } finally {
            setFullPreparing(false);
            setIsChangeAllowed(true);
        }
    };

    const downloadEye = async (kind: 'left' | 'right') => {
        if (!isDepthMapReady || fullPreparing) return;
        setFullPreparing(true);
        setProcessingStage('full');
        try {
            const prepare = await fetch(`${apiUrl}/prepare-full?${renderParams()}`, { method: 'GET', credentials: 'include' });
            if (!prepare.ok) throw new Error(`Full-resolution stereo render failed: ${prepare.status}`);
            const params = new URLSearchParams({scope: 'full', format: downloadFormat, quality: String(jpegQuality), pop_out: String(popOut), max_disparity_percentage: String(appliedStrength)});
            const response = await fetch(`${apiUrl}/output/${kind}?${params.toString()}`, { credentials: 'include' });
            if (!response.ok) throw new Error(`Eye download failed: ${response.status}`);
            triggerBlobDownload(await response.blob(), `${kind}-eye.${downloadFormat === 'png' ? 'png' : 'jpg'}`);
            setProcessingStage('ready');
        } catch (error) {
            console.error(error);
            setProcessingStage('error');
        } finally {
            setFullPreparing(false);
        }
    };

    useEffect(() => {
        const onKeyDown = (event: KeyboardEvent) => {
            if (event.metaKey || event.ctrlKey || event.altKey || event.shiftKey || event.repeat) return;
            const target = event.target as HTMLElement | null;
            if (target && (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName))) return;
            const key = event.key.toLowerCase();
            if (key === 'r') { event.preventDefault(); setActiveTechnique('anaglyph'); }
            else if (key === 'v') { event.preventDefault(); setActiveTechnique('parallel'); }
            else if (key === 'x') { event.preventDefault(); setActiveTechnique('cross'); }
            else if (key === 'f' && previewUrl) { event.preventDefault(); fullscreen(); }
            else if (key === 'd' && previewUrl) { event.preventDefault(); void downloadCurrent(); }
        };
        window.addEventListener('keydown', onKeyDown);
        return () => window.removeEventListener('keydown', onKeyDown);
    }, [activeTechnique, previewUrl, isDepthMapReady, fullPreparing, downloadFormat, jpegQuality, popOut, appliedStrength, optimiseRRAnaglyph, appliedSettings]);

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

    const usesStereo = stereoBasedTechniques.has(activeTechnique);
    const fixedFormat = activeTechnique === 'wiggle' ? 'GIF' : activeTechnique === 'stereoscope' || activeTechnique === 'lenticular' ? 'PNG' : null;
    const info = techniqueInfo[activeTechnique];
    const specialSelected = !basicTechniques.has(activeTechnique);

    return (
        <div className="editorWorkspace">
            <div className="editorHeader">
                <div><div className="panelLabel">OUTPUT</div><h2>3D Technique Studio</h2></div>
                <div className="generationState">{fullPreparing ? <><span className="miniLoader" /> Full resolution</> : outputsAreLoading ? <><span className="miniLoader" /> Rendering {info.label}</> : isDepthMapReady ? "Ready" : "Waiting for image"}</div>
            </div>

            <div className="techniqueChooser">
                <div className="outputTabs">
                    <button className={activeTechnique === 'anaglyph' ? 'outputTab active' : 'outputTab'} onClick={() => setActiveTechnique('anaglyph')}>Red/Cyan <kbd>R</kbd></button>
                    <button className={activeTechnique === 'parallel' ? 'outputTab active' : 'outputTab'} onClick={() => setActiveTechnique('parallel')}>Parallel <kbd>V</kbd></button>
                    <button className={activeTechnique === 'cross' ? 'outputTab active' : 'outputTab'} onClick={() => setActiveTechnique('cross')}>Cross-Eyed <kbd>X</kbd></button>
                </div>
                <select className={specialSelected ? 'moreTechniques active' : 'moreTechniques'} value={specialSelected ? activeTechnique : ''} onChange={(e) => setActiveTechnique(e.target.value as TechniqueId)}>
                    <option value="" disabled>More techniques…</option>
                    <optgroup label="Glasses"><option value="chromadepth">ChromaDepth</option></optgroup>
                    <optgroup label="Viewers"><option value="cardboard">Cardboard / Phone Viewer</option><option value="stereoscope">Traditional Stereoscope Card</option></optgroup>
                    <optgroup label="Animation"><option value="wiggle">Wiggle-gram</option></optgroup>
                    <optgroup label="Autostereograms"><option value="randomdot">Random-Dot Stereogram</option><option value="pattern">Pattern Stereogram</option></optgroup>
                    <optgroup label="Print"><option value="lenticular">Lenticular 3D</option></optgroup>
                </select>
            </div>
            <div className="techniqueSummary"><strong>{info.label}</strong><span>{info.description}</span><em>{info.family}</em></div>

            <div className={`previewFrame ${zoom > 1 ? 'zoomed' : ''}`} ref={previewRef} onPointerDown={beginPan} onPointerMove={movePan} onPointerUp={endPan} onPointerCancel={endPan} onDoubleClick={resetZoom}>
                {previewUrl ? <img src={previewUrl} alt={info.label} draggable={false} style={{maxWidth: `${viewScale}%`, transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`}} /> : (
                    <div className="emptyStage"><div className="stereoGlyph">◉ ◉</div><strong>Your 3D result will appear here</strong><span>Drop, choose, or paste an image in the source panel.</span></div>
                )}
                {outputsAreLoading && <div className="loadingVeil"><div className="largeLoader" /><span>Rendering {info.label}…</span></div>}
            </div>

            <div className="previewMeta">
                <div><strong>{info.label}</strong><span>{info.description}</span></div>
                <div className="previewActions">
                    <div className="zoomControls"><button onClick={() => zoomBy(-0.25)} disabled={zoom <= 1}>−</button><button onClick={resetZoom}>{Math.round(zoom * 100)}%</button><button onClick={() => zoomBy(0.25)} disabled={zoom >= 4}>＋</button></div>
                    <button onClick={fullscreen} disabled={!previewUrl}>Fullscreen <kbd>F</kbd></button>
                    <button className="downloadAction" onClick={() => void downloadCurrent()} disabled={!previewUrl || fullPreparing}>Download <kbd>D</kbd></button>
                </div>
            </div>

            <div className={`settingsCard ${usesStereo ? '' : 'nonStereo'}`}>
                {usesStereo && <div className="settingGroup">
                    <div className="settingTitle"><span>3D strength</span><strong>{sliderValue.toFixed(1)}%</strong></div>
                    <input type="range" min="0" max="6" step="0.1" value={sliderValue} disabled={!isChangeAllowed} onChange={(e) => setSliderValue(parseFloat(e.target.value))} onPointerUp={() => isChangeAllowed && setAppliedStrength(sliderValue)} onKeyUp={() => isChangeAllowed && setAppliedStrength(sliderValue)} />
                    <div className="rangeLabels"><span>Subtle</span><span>{sliderValue !== appliedStrength ? 'Release to apply' : 'Strong'}</span></div>
                </div>}
                <div className="settingGroup">
                    <div className="settingTitle"><span>On-screen preview size</span><strong>{viewScale}%</strong></div>
                    <input type="range" min="35" max="100" step="1" value={viewScale} onChange={(e) => setViewScale(parseInt(e.target.value))} />
                    <div className="rangeLabels"><span>Smaller</span><span>Fill stage</span></div>
                </div>
                {usesStereo && <label className="toggleSetting"><span><strong>Pop out</strong><small>Place depth in front of screen</small></span><input type="checkbox" checked={popOut} disabled={!isChangeAllowed} onChange={(e) => setPopOut(e.target.checked)} /></label>}
                {activeTechnique === 'anaglyph' && <label className="toggleSetting"><span><strong>Reduce retinal rivalry</strong><small>Red/cyan output only</small></span><input type="checkbox" checked={optimiseRRAnaglyph} disabled={!isChangeAllowed} onChange={(e) => setOptimiseRRAnaglyph(e.target.checked)} /></label>}
            </div>

            {specialSelected && <TechniqueControls technique={activeTechnique} settings={draftSettings} setSettings={setDraftSettings} onApply={applyTechniqueSettings} dirty={techniqueDirty} disabled={!isChangeAllowed} apiUrl={apiUrl} />}

            <div className="downloadPanel">
                <div className="downloadHeading"><div><strong>Final output</strong><span>Static techniques render from the full-resolution source. Print-specific formats use their selected physical dimensions and DPI.</span></div><span className="fullResBadge">FULL QUALITY</span></div>
                <div className="downloadControls">
                    {fixedFormat ? <div className="fixedFormat"><span>Format</span><strong>{fixedFormat}</strong></div> : <label>Format<select value={downloadFormat} onChange={(e) => setDownloadFormat(e.target.value as 'jpeg' | 'png')}><option value="jpeg">JPEG</option><option value="png">PNG</option></select></label>}
                    {!fixedFormat && downloadFormat === 'jpeg' && <label>JPEG quality<input type="range" min="70" max="100" step="1" value={jpegQuality} onChange={(e) => setJpegQuality(parseInt(e.target.value))} /><strong>{jpegQuality}</strong></label>}
                    {usesStereo && <div className="eyeDownloads"><button onClick={() => void downloadEye('left')} disabled={!hasRendered || fullPreparing}>Left eye</button><button onClick={() => void downloadEye('right')} disabled={!hasRendered || fullPreparing}>Right eye</button></div>}
                </div>
            </div>
        </div>
    );
}

export default AnaglyphEditor;
