import cv2
import numpy as np


def make_anaglyph(left: np.ndarray, right: np.ndarray, glasses: str = "red-cyan", color_mode: str = "full") -> np.ndarray:
    """Combine a stereo pair for red/cyan, red/green, or red/blue glasses.

    color_mode accepts the legacy strings full/half/gray and also a numeric
    color-retention amount from 0..100. 100 reproduces full color, 50 reproduces
    the previous half-color mode, and 0 reproduces grayscale rendering.
    """
    glasses = glasses.lower()
    if glasses not in {"red-cyan", "red-green", "red-blue"}:
        glasses = "red-cyan"

    raw_mode = str(color_mode).lower()
    legacy_amounts = {"full": 100.0, "half": 50.0, "gray": 0.0}
    if raw_mode in legacy_amounts:
        color_amount = legacy_amounts[raw_mode]
    else:
        try:
            color_amount = float(raw_mode)
        except (TypeError, ValueError):
            color_amount = 100.0
        color_amount = max(0.0, min(100.0, color_amount))

    left_gray = cv2.cvtColor(left, cv2.COLOR_BGR2GRAY).astype(np.float32)
    right_gray = cv2.cvtColor(right, cv2.COLOR_BGR2GRAY).astype(np.float32)
    left_red_full = left[:, :, 2].astype(np.float32)
    right_blue_full = right[:, :, 0].astype(np.float32)
    right_green_full = right[:, :, 1].astype(np.float32)

    # Preserve the three familiar landmarks while allowing continuous adjustment:
    # 100 = full color; 50 = classic half-color; 0 = grayscale.
    if color_amount >= 50.0:
        t = (color_amount - 50.0) / 50.0
        left_red = left_gray * (1.0 - t) + left_red_full * t
        right_blue = right_blue_full
        right_green = right_green_full
    else:
        t = color_amount / 50.0
        left_red = left_gray
        right_blue = right_gray * (1.0 - t) + right_blue_full * t
        right_green = right_gray * (1.0 - t) + right_green_full * t

    output = np.zeros_like(left)
    output[:, :, 2] = np.clip(left_red, 0, 255).astype(np.uint8)
    if glasses == "red-cyan":
        output[:, :, 0] = np.clip(right_blue, 0, 255).astype(np.uint8)
        output[:, :, 1] = np.clip(right_green, 0, 255).astype(np.uint8)
    elif glasses == "red-green":
        output[:, :, 1] = np.clip(right_green, 0, 255).astype(np.uint8)
    else:
        output[:, :, 0] = np.clip(right_blue, 0, 255).astype(np.uint8)
    return output


def compatibility_stereo(left: np.ndarray, right: np.ndarray, kind: str) -> np.ndarray:
    """Package a stereo pair for common display/video compatibility formats."""
    kind = kind.lower()
    if kind == "topbottom":
        return np.vstack((left, right))
    if kind == "halfsbs":
        height, width = left.shape[:2]
        half_width = max(1, width // 2)
        left_half = cv2.resize(left, (half_width, height), interpolation=cv2.INTER_AREA)
        right_half = cv2.resize(right, (width - half_width, height), interpolation=cv2.INTER_AREA)
        return np.hstack((left_half, right_half))
    if kind == "rowinterlaced":
        output = left.copy()
        output[1::2] = right[1::2]
        return output
    if kind == "columninterlaced":
        output = left.copy()
        output[:, 1::2] = right[:, 1::2]
        return output
    if kind == "checkerboard":
        output = left.copy()
        yy, xx = np.indices(left.shape[:2])
        mask = ((xx + yy) % 2) == 1
        output[mask] = right[mask]
        return output
    raise ValueError("Unknown stereo compatibility layout")
