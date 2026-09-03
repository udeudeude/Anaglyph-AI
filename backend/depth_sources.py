import io

import cv2
import numpy as np


def normalise_depth(array: np.ndarray) -> np.ndarray:
    """Convert image/numeric depth data to a finite float32 0..1 map."""
    if array.ndim == 3:
        if array.shape[2] == 4:
            array = cv2.cvtColor(array, cv2.COLOR_BGRA2GRAY)
        else:
            array = cv2.cvtColor(array, cv2.COLOR_BGR2GRAY)
    if array.ndim != 2:
        raise ValueError("Depth map must be a 2D array or an image")

    original_dtype = array.dtype
    depth = np.nan_to_num(array.astype(np.float32), nan=0.0, posinf=1.0, neginf=0.0)
    if np.issubdtype(original_dtype, np.integer):
        maximum = float(np.iinfo(original_dtype).max)
        if maximum > 0:
            depth /= maximum
    else:
        minimum = float(np.min(depth))
        maximum = float(np.max(depth))
        if minimum < 0.0 or maximum > 1.0:
            span = maximum - minimum
            depth = np.zeros_like(depth) if span <= 1e-12 else (depth - minimum) / span
    return np.clip(depth, 0.0, 1.0).astype(np.float32)


def load_depth_upload(upload) -> np.ndarray:
    filename = (upload.filename or "").lower()
    raw = upload.read()
    if not raw:
        raise ValueError("Depth map file is empty")
    if filename.endswith(".npy"):
        return normalise_depth(np.load(io.BytesIO(raw), allow_pickle=False))
    encoded = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(encoded, cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError("Could not read depth map image")
    return normalise_depth(image)


def align_depth(depth: np.ndarray, target_width: int, target_height: int, mode: str = "crop") -> np.ndarray:
    """Align an arbitrary depth-map aspect ratio with the source image."""
    mode = mode.lower()
    if mode not in {"crop", "fit", "stretch"}:
        mode = "crop"
    source_h, source_w = depth.shape[:2]
    if mode == "stretch":
        return np.clip(cv2.resize(depth, (target_width, target_height), interpolation=cv2.INTER_CUBIC), 0.0, 1.0).astype(np.float32)

    source_ratio = source_w / source_h
    target_ratio = target_width / target_height
    if mode == "crop":
        if source_ratio > target_ratio:
            crop_w = max(1, int(round(source_h * target_ratio)))
            x0 = (source_w - crop_w) // 2
            depth = depth[:, x0:x0 + crop_w]
        elif source_ratio < target_ratio:
            crop_h = max(1, int(round(source_w / target_ratio)))
            y0 = (source_h - crop_h) // 2
            depth = depth[y0:y0 + crop_h, :]
        return np.clip(cv2.resize(depth, (target_width, target_height), interpolation=cv2.INTER_CUBIC), 0.0, 1.0).astype(np.float32)

    scale = min(target_width / source_w, target_height / source_h)
    width = max(1, int(round(source_w * scale)))
    height = max(1, int(round(source_h * scale)))
    resized = cv2.resize(depth, (width, height), interpolation=cv2.INTER_CUBIC)
    left = (target_width - width) // 2
    right = target_width - width - left
    top = (target_height - height) // 2
    bottom = target_height - height - top
    fitted = cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_REPLICATE)
    return np.clip(fitted, 0.0, 1.0).astype(np.float32)
