import time

start_import_time = time.time()
import cv2
import torch
import numpy as np
from ai_models.Depth_Anything_V2.depth_anything_v2.dpt import DepthAnythingV2
end_import_time = time.time()
print(f"Elapsed time for imports: {end_import_time - start_import_time:.4f} seconds")


class DepthMapGenerator:
    _instance = None
    model = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DepthMapGenerator, cls).__new__(cls)
        return cls._instance

    def __init__(self, encoder="vits"):
        if self.model is None:
            self.load_model(encoder)

    def load_model(self, encoder):
        print("Loading model")
        device = 'cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu'
        model_configs = {
            'vits': {'encoder': 'vits', 'features': 64, 'out_channels': [48, 96, 192, 384]},
            'vitb': {'encoder': 'vitb', 'features': 128, 'out_channels': [96, 192, 384, 768]},
            'vitl': {'encoder': 'vitl', 'features': 256, 'out_channels': [256, 512, 1024, 1024]},
            'vitg': {'encoder': 'vitg', 'features': 384, 'out_channels': [1536, 1536, 1536, 1536]}
        }
        self.model = DepthAnythingV2(**model_configs[encoder])
        self.model.load_state_dict(torch.load(f'ai_models/checkpoints/depth_anything_v2_{encoder}.pth', map_location='cpu'))
        self.model = self.model.to(device).eval()
        print(f"Loaded model on {device}")

    def generate_depth_map(self, image: np.ndarray) -> np.ndarray:
        """Generate a full-image normalized depth map while the model handles inference resizing internally."""
        return self.normalise(self.model.infer_image(image)).astype(np.float32)

    def normalise(self, depth_map: np.ndarray) -> np.ndarray:
        minimum = float(np.min(depth_map))
        maximum = float(np.max(depth_map))
        span = maximum - minimum
        if span <= 1e-12:
            return np.zeros_like(depth_map, dtype=np.float32)
        return ((depth_map - minimum) / span).astype(np.float32)

    def downscale_image(self, image: np.ndarray, width: int, height: int):
        return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)

    def upscale_depth_map(self, depth_map: np.ndarray, width: int, height: int):
        """Resize floating-point depth without quantizing it to 8-bit first."""
        return cv2.resize(depth_map.astype(np.float32), (width, height), interpolation=cv2.INTER_CUBIC)

    def generate_depth_map_performant(self, image: np.ndarray, intermediateWidth: int, intermediateHeight: int) -> np.ndarray:
        """Legacy helper that preserves source aspect ratio and depth precision."""
        start_time = time.time()
        height, width = image.shape[:2]
        scale = min(intermediateWidth / width, intermediateHeight / height)
        scaled_width = max(1, int(round(width * scale)))
        scaled_height = max(1, int(round(height * scale)))
        image_downscaled = self.downscale_image(image, scaled_width, scaled_height)
        depth_map_downscaled = self.generate_depth_map(image_downscaled)
        depth_map_upscaled = self.upscale_depth_map(depth_map_downscaled, width, height)
        print(f"Elapsed time for depth map generation (performant): {time.time() - start_time:.4f} seconds")
        return np.clip(depth_map_upscaled, 0.0, 1.0).astype(np.float32)

    def colour_depth_map(self, depth_map: np.ndarray) -> np.ndarray:
        depth_map_scaled = (np.clip(depth_map, 0.0, 1.0) * 255).astype(np.uint8)
        return cv2.applyColorMap(depth_map_scaled, cv2.COLORMAP_JET)

    def blur_depth_map(self, depth_map: np.ndarray, kernel_width: int) -> np.ndarray:
        """Blur horizontally while retaining floating-point depth precision."""
        return cv2.blur(depth_map.astype(np.float32), (kernel_width, 1)).astype(np.float32)


depth_map_generator = DepthMapGenerator(encoder="vits")
