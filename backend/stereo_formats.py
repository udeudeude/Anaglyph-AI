import cv2
import numpy as np


def make_anaglyph(left: np.ndarray, right: np.ndarray, glasses: str = "red-cyan", color_mode: str = "full") -> np.ndarray:
    """Combine a stereo pair for red/cyan, red/green, or red/blue glasses."""
    glasses = glasses.lower()
    if glasses not in {"red-cyan", "red-green", "red-blue"}:
        glasses = "red-cyan"
    color_mode = color_mode.lower()
    if color_mode not in {"full", "half", "gray"}:
        color_mode = "full"

    left_gray = cv2.cvtColor(left, cv2.COLOR_BGR2GRAY)
    right_gray = cv2.cvtColor(right, cv2.COLOR_BGR2GRAY)
    left_red = left[:, :, 2] if color_mode == "full" else left_gray
    right_blue = right_gray if color_mode == "gray" else right[:, :, 0]
    right_green = right_gray if color_mode == "gray" else right[:, :, 1]

    output = np.zeros_like(left)
    output[:, :, 2] = left_red
    if glasses == "red-cyan":
        output[:, :, 0] = right_blue
        output[:, :, 1] = right_green
    elif glasses == "red-green":
        output[:, :, 1] = right_green
    else:
        output[:, :, 0] = right_blue
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
