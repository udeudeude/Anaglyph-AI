"""Physical-plane phantogram projection.

Coordinates are millimetres. The print lies on z=0, x spans its width, and y runs
from the near edge toward the far edge. The viewer is at y=-view_distance.
Depth is interpreted as relief height above the print, not as an arbitrary 2-D warp.
"""
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def fit_to_print(image, depth, width, height):
    """Center-crop source and depth together, then resize to the physical print raster."""
    source_h, source_w = image.shape[:2]
    source_ratio = source_w / source_h
    target_ratio = width / height
    if source_ratio > target_ratio:
        crop_w = max(1, int(round(source_h * target_ratio)))
        x0 = (source_w - crop_w) // 2
        image = image[:, x0:x0 + crop_w]
        depth = depth[:, x0:x0 + crop_w]
    elif source_ratio < target_ratio:
        crop_h = max(1, int(round(source_w / target_ratio)))
        y0 = (source_h - crop_h) // 2
        image = image[y0:y0 + crop_h, :]
        depth = depth[y0:y0 + crop_h, :]
    image = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA if width < image.shape[1] else cv2.INTER_CUBIC)
    depth = cv2.resize(depth.astype(np.float32), (width, height), interpolation=cv2.INTER_CUBIC)
    return image, np.clip(depth, 0.0, 1.0).astype(np.float32)


def project_relief(image, depth, print_width_mm, print_height_mm, view_distance_mm,
                   eye_height_mm, eye_x_mm, relief_mm, reverse_depth=False):
    h, w = image.shape[:2]
    if depth.shape != (h, w):
        depth = cv2.resize(depth.astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
    d = np.clip(depth.astype(np.float32), 0.0, 1.0)
    if reverse_depth:
        d = 1.0 - d
    z = d * max(0.0, float(relief_mm))
    xs = np.linspace(-print_width_mm / 2.0, print_width_mm / 2.0, w, dtype=np.float32)[None, :]
    ys = np.linspace(0.0, print_height_mm, h, dtype=np.float32)[:, None]
    eye_y = -max(1.0, float(view_distance_mm))
    eye_z = max(float(relief_mm) + 1.0, float(eye_height_mm))

    # Ray from each eye through each relief point intersects the physical print plane z=0.
    t = eye_z / np.maximum(1e-6, eye_z - z)
    px = eye_x_mm + t * (xs - eye_x_mm)
    py = eye_y + t * (ys - eye_y)
    u = np.rint((px / print_width_mm + 0.5) * (w - 1)).astype(np.int32)
    v = np.rint((py / print_height_mm) * (h - 1)).astype(np.int32)

    out = np.zeros_like(image)
    occupied = np.zeros((h, w), dtype=np.uint8)
    # Painter's algorithm: higher relief is nearer the eye and wins collisions.
    order = np.argsort(z.ravel())
    src_y, src_x = np.indices((h, w))
    flat_y = src_y.ravel()[order]
    flat_x = src_x.ravel()[order]
    dest_x = u.ravel()[order]
    dest_y = v.ravel()[order]
    valid = (dest_x >= 0) & (dest_x < w) & (dest_y >= 0) & (dest_y < h)
    dx = dest_x[valid]
    dy = dest_y[valid]
    out[dy, dx] = image[flat_y[valid], flat_x[valid]]
    occupied[dy, dx] = 255
    holes = cv2.bitwise_not(occupied)
    if np.any(holes):
        out = cv2.inpaint(out, holes, 2, cv2.INPAINT_TELEA)
    return out


def render_phantogram(image, depth, print_width_mm=203.2, print_height_mm=152.4,
                       view_distance_mm=508.0, eye_height_mm=355.6, ipd_mm=63.0,
                       relief_mm=35.0, glasses='red-cyan', reverse_depth=False):
    left = project_relief(image, depth, print_width_mm, print_height_mm, view_distance_mm,
                          eye_height_mm, -ipd_mm / 2.0, relief_mm, reverse_depth)
    right = project_relief(image, depth, print_width_mm, print_height_mm, view_distance_mm,
                           eye_height_mm, ipd_mm / 2.0, relief_mm, reverse_depth)
    out = np.zeros_like(image)
    if glasses == 'red-green':
        out[:, :, 2] = left[:, :, 2]
        out[:, :, 1] = right[:, :, 1]
    elif glasses == 'red-blue':
        out[:, :, 2] = left[:, :, 2]
        out[:, :, 0] = right[:, :, 0]
    else:
        out[:, :, 2] = left[:, :, 2]
        out[:, :, 1] = right[:, :, 1]
        out[:, :, 0] = right[:, :, 0]
    return out, left, right


def calibration_ruler(dpi=300):
    """Return a small PNG-ready image containing a physically exact 100 mm ruler."""
    dpi = max(72, min(1200, int(dpi)))
    px_per_mm = dpi / 25.4
    width_mm, height_mm = 120.0, 28.0
    width = int(round(width_mm * px_per_mm))
    height = int(round(height_mm * px_per_mm))
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    y = int(round(13 * px_per_mm))
    x0 = int(round(10 * px_per_mm))
    x1 = int(round(110 * px_per_mm))
    line = max(1, int(round(0.35 * px_per_mm)))
    draw.line((x0, y, x1, y), fill='black', width=line)
    for mm in range(0, 101, 10):
        x = int(round((10 + mm) * px_per_mm))
        tick = 5 if mm % 50 == 0 else 3
        draw.line((x, y - int(round(tick * px_per_mm)), x, y + int(round(tick * px_per_mm))), fill='black', width=line)
        draw.text((x, y + int(round(5 * px_per_mm))), str(mm), fill='black', anchor='ma')
    draw.text((width // 2, int(round(2 * px_per_mm))), '100 mm PRINT CHECK - PRINT AT 100% / ACTUAL SIZE', fill='black', anchor='ma')
    return image
