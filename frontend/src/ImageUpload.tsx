import {useState, useRef} from "react";
import "./styles/ImageUpload.css";

// @ts-ignore
function ImageUpload({ setIsDepthMapReadyStateLifter, isChangeAllowed, setIsChangeAllowed }) {
    const imageInputRef = useRef<HTMLInputElement>(null);
    const [imageUrl, setImageUrl] = useState<string | null>(null);
    const [depthMapUrl, setDepthMapUrl] = useState<string | null>(null);
    const [depthMapIsLoading, setDepthMapIsLoading] = useState<boolean>(false);
    const apiUrl = import.meta.env.VITE_FLASK_BACKEND_API_URL || "http://localhost:8000";
    const maxDimension = Number(import.meta.env.VITE_MAX_DIMENSION || 1500);

    const fetchDepthMap = async () => {
        try {
            const response = await fetch(`${apiUrl}/depth-map`, { method: "GET", credentials: "include" });
            if (!response.ok) throw new Error(response.statusText);
            const blob = await response.blob();
            if (!blob.size) throw new Error("Depth map is empty");
            setDepthMapUrl(URL.createObjectURL(blob));
            setIsDepthMapReadyStateLifter(true);
        } catch (error) {
            console.error("Failed to fetch depth map", error);
            setIsChangeAllowed(true);
        } finally {
            setDepthMapIsLoading(false);
        }
    };

    const handleImageUpload = async (imageFile: File) => {
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");
        const image = new Image();
        const sourceObjectUrl = URL.createObjectURL(imageFile);
        image.onload = async () => {
            let width = image.width;
            let height = image.height;
            const scale = Math.min(1, maxDimension / Math.max(width, height));
            width = Math.round(width * scale);
            height = Math.round(height * scale);
            canvas.width = width;
            canvas.height = height;
            ctx?.drawImage(image, 0, 0, width, height);
            canvas.toBlob(async (blob) => {
                URL.revokeObjectURL(sourceObjectUrl);
                if (!blob) { setIsChangeAllowed(true); return; }
                setImageUrl(URL.createObjectURL(blob));
                setDepthMapUrl(null);
                setDepthMapIsLoading(true);
                const formData = new FormData();
                formData.append("file", blob, imageFile.name);
                try {
                    setIsDepthMapReadyStateLifter(false);
                    const response = await fetch(`${apiUrl}/image`, { method: "POST", body: formData, credentials: "include" });
                    if (!response.ok) throw new Error(`Upload failed: ${response.status}`);
                    fetchDepthMap();
                } catch (error) {
                    console.error("Failed to upload image", error);
                    setDepthMapIsLoading(false);
                    setIsChangeAllowed(true);
                }
            }, "image/jpeg", 0.94);
        };
        image.src = sourceObjectUrl;
    };

    const handleImageChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;
        setIsChangeAllowed(false);
        await handleImageUpload(file);
    };

    const handleRandomButtonClick = async () => {
        if (!isChangeAllowed && imageUrl) return;
        setIsChangeAllowed(false);
        setIsDepthMapReadyStateLifter(false);
        try {
            const response = await fetch(`${apiUrl}/random_image`, { method: "GET", credentials: "include" });
            if (!response.ok) throw new Error(response.statusText);
            const blob = await response.blob();
            setImageUrl(URL.createObjectURL(blob));
            setDepthMapUrl(null);
            setDepthMapIsLoading(true);
            fetchDepthMap();
        } catch (error) {
            console.error("Failed to fetch random image", error);
            setIsChangeAllowed(true);
        }
    };

    return (
        <div className="sourcePanel">
            <div className="panelLabel">SOURCE</div>
            <button className="primaryAction" onClick={() => imageInputRef.current?.click()} disabled={!isChangeAllowed && !!imageUrl}>
                <span className="buttonIcon">＋</span> Choose image
            </button>
            <button className="secondaryAction" onClick={handleRandomButtonClick} disabled={!isChangeAllowed && !!imageUrl}>Random example</button>
            <input type="file" accept="image/jpeg,image/jpg,image/png,image/webp" ref={imageInputRef} className="hiddenInput" onClick={(e) => { e.currentTarget.value = ""; }} onChange={handleImageChange} />

            <div className="sourcePreview">
                {imageUrl ? <img src={imageUrl} alt="Source" /> : <div className="emptyPreview">Select a photograph to begin</div>}
            </div>

            <div className="depthHeader"><span>AI depth map</span>{depthMapIsLoading && <span className="miniLoader" />}</div>
            <div className="depthPreview">
                {depthMapUrl ? <img src={depthMapUrl} alt="AI depth map" /> : <div className="depthPlaceholder">Depth estimation appears here</div>}
            </div>

            <div className="localNote"><strong>Depth Anything V2</strong><span>Images are processed by the model running on this computer.</span></div>
        </div>
    );
}

export default ImageUpload;
