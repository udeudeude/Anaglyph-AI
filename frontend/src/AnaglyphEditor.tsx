import { useState, useEffect } from "react";
import "./styles/AnaglyphEditor.css";

type OutputKind = "anaglyph" | "parallel" | "cross";

function AnaglyphEditor({ isDepthMapReady, isChangeAllowed, setIsChangeAllowed}: { isDepthMapReady: boolean, isChangeAllowed: boolean, setIsChangeAllowed: (value: boolean) => void}) {
    const apiUrl = import.meta.env.VITE_FLASK_BACKEND_API_URL || "http://localhost:8000";
    const [outputUrls, setOutputUrls] = useState<Record<OutputKind, string | null>>({
        anaglyph: null,
        parallel: null,
        cross: null,
    });
    const [outputsAreLoading, setOutputsAreLoading] = useState<boolean>(false);

    const [popOut, setPopOut] = useState<boolean>(false);
    const [maxDisparityPercentage, setMaxDisparityPercentage] = useState<number>(2);
    const [optimiseRRAnaglyph, setOptimiseRRAnaglyph] = useState<boolean>(false);
    const [sliderValue, setSliderValue] = useState<number>(2);

    useEffect(() => {
        if (isDepthMapReady) {
            fetchOutputs();
        }
    }, [isDepthMapReady, popOut, maxDisparityPercentage, optimiseRRAnaglyph]);

    useEffect(() => {
        setIsChangeAllowed(!outputsAreLoading);
    }, [outputsAreLoading]);

    useEffect(() => {
        return () => {
            Object.values(outputUrls).forEach((url) => {
                if (url) URL.revokeObjectURL(url);
            });
        };
    }, []);

    const commonParams = () =>
        `pop_out=${popOut}&max_disparity_percentage=${maxDisparityPercentage}`;

    const fetchBlob = async (url: string) => {
        const response = await fetch(url, { method: "GET", credentials: "include" });
        if (!response.ok) {
            throw new Error(`Request failed with status ${response.status}`);
        }
        return response.blob();
    };

    const fetchOutputs = async () => {
        setOutputsAreLoading(true);
        try {
            const params = commonParams();
            const [anaglyphBlob, parallelBlob, crossBlob] = await Promise.all([
                fetchBlob(`${apiUrl}/anaglyph?${params}&optimised_RR_anaglyph=${optimiseRRAnaglyph}`),
                fetchBlob(`${apiUrl}/stereo-pair?mode=parallel&${params}`),
                fetchBlob(`${apiUrl}/stereo-pair?mode=cross&${params}`),
            ]);

            setOutputUrls((oldUrls) => {
                Object.values(oldUrls).forEach((url) => {
                    if (url) URL.revokeObjectURL(url);
                });
                return {
                    anaglyph: URL.createObjectURL(anaglyphBlob),
                    parallel: URL.createObjectURL(parallelBlob),
                    cross: URL.createObjectURL(crossBlob),
                };
            });
        } catch (error) {
            console.error("Failed to fetch 3D outputs", error);
        } finally {
            setOutputsAreLoading(false);
        }
    };

    const handleSliderChange = (e: { target: { value: string } }) => {
        if (isChangeAllowed) setSliderValue(parseFloat(e.target.value));
    };

    const handleSliderReleased = () => {
        if (isChangeAllowed) setMaxDisparityPercentage(sliderValue);
    };

    const handleDownload = (kind: OutputKind) => {
        const url = outputUrls[kind];
        if (!url) return;
        const filenames: Record<OutputKind, string> = {
            anaglyph: "anaglyph.jpeg",
            parallel: "parallel-stereo.jpeg",
            cross: "cross-eyed-stereo.jpeg",
        };
        const link = document.createElement("a");
        link.href = url;
        link.download = filenames[kind];
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const outputCards: { kind: OutputKind; title: string; description: string }[] = [
        { kind: "anaglyph", title: "Red / Cyan Anaglyph", description: "View with red-cyan 3D glasses." },
        { kind: "parallel", title: "Parallel Stereo", description: "Left-eye image on the left; view with relaxed (wall-eyed) convergence." },
        { kind: "cross", title: "Cross-Eyed Stereo", description: "Right-eye image on the left; cross your eyes until the two views fuse." },
    ];

    return (
        <div>
            <h1>3D Image Generator</h1>
            <div className="anaglyphEditor">
                <form>
                    <label>
                        Pop Out
                        <input
                            type="checkbox"
                            checked={popOut}
                            onChange={(e) => isChangeAllowed && setPopOut(e.target.checked)}
                        />
                    </label>
                </form>
                <form>
                    <label>
                        Strength
                        <input
                            type="range"
                            min="0"
                            max="6"
                            step="0.1"
                            value={sliderValue}
                            onChange={handleSliderChange}
                            onMouseUp={handleSliderReleased}
                            onTouchEnd={handleSliderReleased}
                        />
                        {sliderValue.toFixed(1)}%
                    </label>
                </form>
                <form>
                    <label>
                        Minimise Retinal Rivalry (anaglyph only)
                        <input
                            type="checkbox"
                            checked={optimiseRRAnaglyph}
                            onChange={(e) => isChangeAllowed && setOptimiseRRAnaglyph(e.target.checked)}
                        />
                    </label>
                </form>
            </div>

            <div className="outputStatus">
                {outputsAreLoading && isDepthMapReady && <div className="loader"></div>}
            </div>

            <div className="stereoOutputs">
                {outputCards.map(({ kind, title, description }) => (
                    <section className="stereoOutputCard" key={kind}>
                        <div className="stereoOutputHeader">
                            <div>
                                <h2>{title}</h2>
                                <p>{description}</p>
                            </div>
                            {outputUrls[kind] && !outputsAreLoading && (
                                <button className="anaglyphButton" onClick={() => handleDownload(kind)}>
                                    Download
                                </button>
                            )}
                        </div>
                        {outputUrls[kind] && (
                            <img src={outputUrls[kind]!} alt={title} className="anaglyphImage" />
                        )}
                    </section>
                ))}
            </div>
        </div>
    );
}

export default AnaglyphEditor;
