import {useState, useRef} from "react";
import "./styles/ImageUpload.css";
import ResizeObserver from 'react-resize-observer'; // To trigger re calculation of image pair layout on window resize

// @ts-ignore
function ImageUpload({ setIsDepthMapReadyStateLifter, isChangeAllowed, setIsChangeAllowed }) {
    const imageInputRef = useRef<HTMLInputElement>(null);
    const [imageUrl, setImageUrl] = useState<string | null>(null);
    const [depthMapUrl, setDepthMapUrl] = useState<string | null>(null);
    const [depthMapIsLoading, setDepthMapIsLoading] = useState<boolean>(false);
    const apiUrl = import.meta.env.VITE_FLASK_BACKEND_API_URL || "http://localhost:8000";
    const maxDimension = Number(import.meta.env.VITE_MAX_DIMENSION || 1500);
    const [imageAspectRatio, setImageAspectRatio] = useState<number>(0); // width / height
    const [windowDimensions, setWindowDimensions] = useState({
        width: window.innerWidth,
        height: window.innerHeight,
    }); // State just to change, so that the component re-renders

    const handleImageChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        // Uploading, so block the upload buttons
        setIsChangeAllowed(false);

        const files = event.target.files;
        if (files && files.length > 0) {
            const selectedImage = files[0]; // Get the selected image file
            console.log("Selected file:", selectedImage); // Log selected file
            await handleImageUpload(selectedImage); // Call upload function
        } else {
            console.error("No files selected");
        }
    };

    const handleImageUpload = async (imageFile: File) => {
        const formData = new FormData();

        // Resize image client-side to reduce processing time and transfer size.
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");
        const image = new Image();

        image.onload = async () => {

            let width = image.width;
            let height = image.height;

            if (width > height) {
                if (width > maxDimension) {
                    height *= maxDimension / width;
                    width = maxDimension;
                }
            } else {
                if (height > maxDimension) {
                    width *= maxDimension / height;
                    height = maxDimension;
                }
            }

            canvas.width = width;
            canvas.height = height;

            // Set the image aspect ratio to the width / height for choosing row or column
            setImageAspectRatio(width / height);

            // @ts-ignore
            ctx.drawImage(image, 0, 0, width, height);

            // Now send the image to the backend
            canvas.toBlob(async (blob) => {
                if (blob) {
                    // Display the image they uploaded as soon as possible
                    const imageUrl = URL.createObjectURL(blob);
                    setImageUrl(imageUrl);

                    formData.append("file", blob, imageFile.name);
                    console.log("Uploading image...");

                    try {
                        setIsDepthMapReadyStateLifter(false); // Set depth map ready to false to stop rendering output editor
                        const response = await fetch(`${apiUrl}/image`, {
                            method: "POST",
                            body: formData,
                            credentials: "include",
                        });
                        console.log("Response status:", response.status);
                        if (response.ok) {
                            const data = await response.json();
                            console.log("Upload successful:", data);

                            setDepthMapUrl(null); // Unload the previous depth map image so the container fits the new image
                            setDepthMapIsLoading(true); // Start loading spinner
                            // Don't use await, causes error where depth map is not shown
                            fetchDepthMap();
                        } else {
                            console.error("Failed to upload image", response.json());
                            setIsChangeAllowed(true);
                        }
                    } catch (error) {
                        console.error("Failed to upload image", error);
                        setIsChangeAllowed(true);
                    }
                }
            }, "image/jpeg");
        };

        image.src = URL.createObjectURL(imageFile);
    };


    const handleRandomButtonClick = async () => {
        // Check if change is allowed (so image upload, depth map retrieval and 3D output generation is done)
        // but allow it if no image has been uploaded yet
        if (isChangeAllowed == false && imageUrl != null) return;
        try {
            setIsDepthMapReadyStateLifter(false); // Set depth map ready to false to stop rendering output editor
            setIsChangeAllowed(false);
            const response = await fetch(`${apiUrl}/random_image`, {
                method: "GET",
                credentials: "include",
            });
            if (response.ok) {
                const randomImageBlob = await response.blob();
                if (randomImageBlob.size === 0) {
                    console.error("Random image is empty");
                    setIsChangeAllowed(true);
                    return;
                }
                const randomImageUrl = URL.createObjectURL(randomImageBlob);
                setDepthMapUrl(null);
                setDepthMapIsLoading(true);
                setImageUrl(randomImageUrl);

                const image = new Image();
                image.onload = () => {
                    setImageAspectRatio(image.width / image.height);
                };
                image.src = randomImageUrl;

                fetchDepthMap();
            } else {
                console.error("Failed to fetch random image", response.statusText);
                setIsChangeAllowed(true);
            }
        } catch (error) {
            console.error("Failed to fetch random image", error);
            setIsChangeAllowed(true);
        }
    }

    const fetchDepthMap = async () => {
        try {
            const response = await fetch(`${apiUrl}/depth-map`, {
                method: "GET",
                credentials: "include",
            });
            if (response.ok) {
                const depthMapBlob = await response.blob();
                if (depthMapBlob.size === 0) {
                    console.error("Depth map is empty");
                    setDepthMapIsLoading(false);
                    setIsChangeAllowed(true);
                    return;
                }
                const depthMapUrl = URL.createObjectURL(depthMapBlob);
                setDepthMapIsLoading(false);
                setDepthMapUrl(depthMapUrl);
                console.log("Depth map fetched successfully", depthMapUrl);
                setIsDepthMapReadyStateLifter(true);

            } else {
                console.error("Failed to fetch depth map", response.statusText);
                setDepthMapIsLoading(false);
                setIsChangeAllowed(true);
            }
        } catch (error) {
            console.error("Failed to fetch depth map", error);
            setDepthMapIsLoading(false);
            setIsChangeAllowed(true);
        }
    }

     const handleUploadButtonClick = () => {
        // Check if the change is allowed (so image upload, depth map retrieval and 3D generation is done)
         // but allow it if no image has been uploaded yet
        if (isChangeAllowed == false && imageUrl != null) return;
        if (imageInputRef.current) {
            imageInputRef.current.click();
        }
    };

    const aspectRatioAndAreaDimensionsToCoveredArea = (aspectRatio: number, areaWidth: number, areaHeight: number) => {
        let width = areaWidth;
        let height = width / aspectRatio;
        if (height > areaHeight) {
            height = areaHeight;
            width = height * aspectRatio;
        }
        return width * height;
    }

    const imagePairBestSpaceLayout = () => {
        const rowAspectRatio = imageAspectRatio * 2;
        const columnAspectRatio = imageAspectRatio / 2;

        // If these display sizes change in CSS, update them here as well.
        const areaWidth = windowDimensions.width * 0.95;
        const areaHeight = windowDimensions.height * 0.7;

        const rowArea = aspectRatioAndAreaDimensionsToCoveredArea(rowAspectRatio, areaWidth, areaHeight);
        const columnArea = aspectRatioAndAreaDimensionsToCoveredArea(columnAspectRatio, areaWidth, areaHeight);

        if (rowArea > columnArea) {
            return (
                <div className="imagePairContainerRow">
                    <div className="imagePairLeftRow">
                        <img src={imageUrl!} alt="Uploaded" className="image" />
                    </div>
                    {depthMapIsLoading && <div className="loader"></div>}
                    {depthMapUrl && (
                    <div className="imagePairRightRow">
                        <img src={depthMapUrl!} alt="Depth Map" className="image" />
                    </div>
                    )}
                </div>
            );
        } else {
            return (
                <div className="imagePairContainerColumn">
                    <div className="imagePairLeftColumn">
                        <img src={imageUrl!} alt="Uploaded" className="image" />
                    </div>
                    {depthMapIsLoading && <div className="loader"></div>}
                    {depthMapUrl && (
                    <div className="imagePairRightColumn">
                        <img src={depthMapUrl!} alt="Depth Map" className="image" />
                    </div>
                    )}
                </div>
            );
        }
    }

    return (
        <div>
            {imageUrl && imagePairBestSpaceLayout()}
            <ResizeObserver
                onResize={() => {
                    setWindowDimensions({ width: window.innerWidth, height: window.innerHeight });
                }}
            />

           <div style={{ display: "flex", justifyContent: "center", marginBottom: "10px" }}>
                <div style={{ display: "flex", justifyContent: "right", width: "50%" }}>
                    <button onClick={handleUploadButtonClick} className="anaglyphButton">
                        Upload Image
                    </button>
                </div>
                <div style={{ display: "flex", justifyContent: "left", width: "50%" }}>
                    <button onClick={handleRandomButtonClick} className="anaglyphButton">
                        Random Image
                    </button>
                </div>
            </div>

            <input
                type="file"
                accept="image/jpeg, image/jpg, image/gif, image/png"
                ref={imageInputRef}
                style={{ display: "none" }}
                onClick={(event) => {
                    event.currentTarget.value = "";}}
                onChange={handleImageChange}
            />
        </div>
    );
}

export default ImageUpload;
