import math
import os
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


class TechniqueGenerator:
    """Render presentation formats that sit on top of the shared source/depth pipeline."""

    @staticmethod
    def _fill_holes(image: np.ndarray) -> np.ndarray:
        mask = np.all(image == -1, axis=-1).astype(np.uint8) * 255
        return cv2.inpaint(image.astype(np.uint8), mask, 1, cv2.INPAINT_TELEA)

    def generate_view(
        self,
        image: np.ndarray,
        depth_map: np.ndarray,
        offset: float,
        pop_out: bool = False,
        strength: float = 2.0,
    ) -> np.ndarray:
        """Synthesize one virtual viewpoint; offset -1..1 spans the stereo baseline."""
        height, width = image.shape[:2]
        depth = depth_map if pop_out else 1.0 - depth_map
        max_shift = (strength / 100.0 * width) / 2.0
        shifts = np.rint(offset * max_shift * depth).astype(np.int32)
        cols = np.arange(width)
        target_cols = np.clip(cols + shifts, 0, width - 1)
        rows = np.arange(height).reshape(height, 1)
        result = np.full_like(image, -1, dtype=np.int16)
        if offset < 0:
            result[rows, target_cols[:, ::-1]] = image[:, ::-1]
        else:
            result[rows, target_cols] = image
        return self._fill_holes(result)

    @staticmethod
    def _fit_bgr(image: np.ndarray, width: int, height: int, background=(0, 0, 0)) -> np.ndarray:
        canvas = np.full((height, width, 3), background, dtype=np.uint8)
        source_h, source_w = image.shape[:2]
        scale = min(width / source_w, height / source_h)
        new_w = max(1, int(round(source_w * scale)))
        new_h = max(1, int(round(source_h * scale)))
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
        x = (width - new_w) // 2
        y = (height - new_h) // 2
        canvas[y:y + new_h, x:x + new_w] = resized
        return canvas

    @staticmethod
    def _crop_resize_pair(image: np.ndarray, depth: np.ndarray, width: int, height: int):
        source_h, source_w = image.shape[:2]
        source_ratio = source_w / source_h
        target_ratio = width / height
        if source_ratio > target_ratio:
            crop_w = int(round(source_h * target_ratio))
            x0 = (source_w - crop_w) // 2
            image = image[:, x0:x0 + crop_w]
            depth = depth[:, x0:x0 + crop_w]
        elif source_ratio < target_ratio:
            crop_h = int(round(source_w / target_ratio))
            y0 = (source_h - crop_h) // 2
            image = image[y0:y0 + crop_h, :]
            depth = depth[y0:y0 + crop_h, :]
        image = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
        depth = cv2.resize(depth.astype(np.float32), (width, height), interpolation=cv2.INTER_CUBIC)
        return image, np.clip(depth, 0.0, 1.0).astype(np.float32)

    def chromadepth(self, image: np.ndarray, depth: np.ndarray, color_strength: float = 0.9, reverse: bool = False) -> np.ndarray:
        depth_use = 1.0 - depth if reverse else depth
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
        # OpenCV hue: red=0, blue≈120. Depth map is 0 near, 1 far.
        target_hue = np.clip(depth_use * 120.0, 0, 120)
        amount = max(0.0, min(1.0, color_strength))
        hsv[:, :, 0] = target_hue
        hsv[:, :, 1] = hsv[:, :, 1] * (1.0 - amount) + 255.0 * amount
        return cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR)

    def cardboard(
        self,
        left: np.ndarray,
        right: np.ndarray,
        output_width: int = 1920,
        output_height: int = 1080,
        screen_width_mm: float = 121.0,
        lens_separation_mm: float = 63.0,
        image_scale: float = 0.92,
    ) -> np.ndarray:
        output_width = max(640, min(5000, int(output_width)))
        output_height = max(360, min(3000, int(output_height)))
        screen_width_mm = max(70.0, min(200.0, float(screen_width_mm)))
        lens_separation_mm = max(45.0, min(80.0, float(lens_separation_mm)))
        image_scale = max(0.3, min(1.0, float(image_scale)))
        canvas = np.zeros((output_height, output_width, 3), dtype=np.uint8)
        px_per_mm = output_width / screen_width_mm
        center = output_width / 2.0
        centers = (
            center - lens_separation_mm * px_per_mm / 2.0,
            center + lens_separation_mm * px_per_mm / 2.0,
        )
        box_w = max(1, int(output_width * 0.48 * image_scale))
        box_h = max(1, int(output_height * 0.96 * image_scale))
        for source, eye_center in ((left, centers[0]), (right, centers[1])):
            fitted = self._fit_bgr(source, box_w, box_h)
            x0 = int(round(eye_center - box_w / 2))
            y0 = (output_height - box_h) // 2
            src_x0 = max(0, -x0)
            dst_x0 = max(0, x0)
            copy_w = min(box_w - src_x0, output_width - dst_x0)
            if copy_w > 0:
                canvas[y0:y0 + box_h, dst_x0:dst_x0 + copy_w] = fitted[:, src_x0:src_x0 + copy_w]
        return canvas

    @staticmethod
    def _font(size: int, bold: bool = False):
        candidates = [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, max(8, int(size)))
                except OSError:
                    continue
        return ImageFont.load_default()

    @staticmethod
    def _arched_mask(width: int, height: int, arch_depth: int) -> Image.Image:
        mask = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(mask)
        arch_depth = max(0, min(height // 3, arch_depth))
        points = []
        for x in range(width):
            normalized = (2.0 * x / max(1, width - 1)) - 1.0
            y = int(round(arch_depth * normalized * normalized))
            points.append((x, y))
        points.extend([(width - 1, height - 1), (0, height - 1)])
        draw.polygon(points, fill=255)
        return mask

    def stereoscope_card(
        self,
        left: np.ndarray,
        right: np.ndarray,
        dpi: int = 300,
        card_width_in: float = 7.0,
        card_height_in: float = 3.5,
        image_width_in: float = 2.85,
        image_height_in: float = 2.55,
        gap_in: float = 0.35,
        arch_in: float = 0.22,
        title: str = "STEREOSCOPIC VIEW",
        caption: str = "Generated from a single photograph",
        publisher: str = "Anaglyph & Friends",
        card_tone: str = "cream",
    ) -> np.ndarray:
        dpi = max(72, min(1200, int(dpi)))
        cw = max(600, int(round(card_width_in * dpi)))
        ch = max(300, int(round(card_height_in * dpi)))
        iw = max(120, int(round(image_width_in * dpi)))
        ih = max(120, int(round(image_height_in * dpi)))
        gap = max(0, int(round(gap_in * dpi)))
        arch = max(0, int(round(arch_in * dpi)))
        tones = {
            "cream": (235, 224, 198),
            "tan": (205, 184, 148),
            "gray": (190, 190, 185),
            "black": (28, 28, 28),
            "white": (245, 245, 242),
        }
        bg = tones.get(card_tone.lower(), tones["cream"])
        fg = (235, 235, 235) if card_tone.lower() == "black" else (32, 28, 24)
        card = Image.new("RGB", (cw, ch), bg)
        total_width = iw * 2 + gap
        x0 = max(0, (cw - total_width) // 2)
        y0 = max(0, int(round(0.14 * dpi)))
        mask = self._arched_mask(iw, ih, arch)
        for source, x in ((left, x0), (right, x0 + iw + gap)):
            rgb = cv2.cvtColor(source, cv2.COLOR_BGR2RGB)
            fitted = ImageOps.fit(Image.fromarray(rgb), (iw, ih), method=Image.Resampling.LANCZOS)
            card.paste(fitted, (x, y0), mask)
        draw = ImageDraw.Draw(card)
        text_top = min(ch - int(0.55 * dpi), y0 + ih + int(0.08 * dpi))
        title_font = self._font(int(0.14 * dpi), bold=True)
        caption_font = self._font(int(0.105 * dpi))
        publisher_font = self._font(int(0.085 * dpi))

        def centered(text: str, y: int, font):
            if not text:
                return
            box = draw.textbbox((0, 0), text, font=font)
            draw.text(((cw - (box[2] - box[0])) / 2, y), text, fill=fg, font=font)

        centered(title[:100], text_top, title_font)
        centered(caption[:160], text_top + int(0.19 * dpi), caption_font)
        centered(publisher[:120], text_top + int(0.37 * dpi), publisher_font)
        return cv2.cvtColor(np.array(card), cv2.COLOR_RGB2BGR)

    @staticmethod
    def _default_pattern(height: int, width: int, style: str = "geometric") -> np.ndarray:
        if style == "checker":
            tile = max(4, width // 12)
            yy, xx = np.indices((height, width))
            checker = ((xx // tile + yy // tile) % 2) * 255
            return cv2.cvtColor(checker.astype(np.uint8), cv2.COLOR_GRAY2BGR)
        rng = np.random.default_rng(1977)
        block = max(3, width // 28)
        small_h = max(1, math.ceil(height / block))
        small_w = max(1, math.ceil(width / block))
        colors = rng.integers(40, 256, size=(small_h, small_w, 3), dtype=np.uint8)
        return cv2.resize(colors, (width, height), interpolation=cv2.INTER_NEAREST)

    def autostereogram(
        self,
        depth: np.ndarray,
        style: str = "random",
        separation_percent: float = 8.0,
        depth_percent: float = 2.3,
        dot_size: int = 3,
        viewing: str = "parallel",
        pattern: Optional[np.ndarray] = None,
        color: bool = False,
    ) -> np.ndarray:
        height, width = depth.shape[:2]
        separation = max(16, int(round(width * separation_percent / 100.0)))
        max_shift = max(1, int(round(width * depth_percent / 100.0)))
        max_shift = min(max_shift, separation - 2)
        if style == "pattern":
            if pattern is None:
                base = self._default_pattern(height, separation, "geometric")
            else:
                source_h, source_w = pattern.shape[:2]
                scale = max(height / source_h, separation / source_w)
                resized = cv2.resize(pattern, (max(separation, int(source_w * scale)), max(height, int(source_h * scale))), interpolation=cv2.INTER_AREA)
                base = resized[:height, :separation]
        else:
            dot_size = max(1, min(12, int(dot_size)))
            rng = np.random.default_rng(314159)
            small_h = max(1, math.ceil(height / dot_size))
            small_w = max(1, math.ceil(separation / dot_size))
            if color:
                seed = rng.integers(0, 256, size=(small_h, small_w, 3), dtype=np.uint8)
            else:
                seed = (rng.integers(0, 2, size=(small_h, small_w, 1), dtype=np.uint8) * 255)
                seed = np.repeat(seed, 3, axis=2)
            base = cv2.resize(seed, (separation, height), interpolation=cv2.INTER_NEAREST)
        output = np.zeros((height, width, 3), dtype=np.uint8)
        output[:, :separation] = base
        rows = np.arange(height)
        depth_use = 1.0 - depth if viewing == "cross" else depth
        for x in range(separation, width):
            sep = separation - np.rint((1.0 - depth_use[:, x]) * max_shift).astype(np.int32)
            source_x = np.clip(x - sep, 0, x - 1)
            output[:, x] = output[rows, source_x]
        return output

    def wiggle_frames(
        self,
        image: np.ndarray,
        depth: np.ndarray,
        frame_count: int = 7,
        strength: float = 2.0,
        pop_out: bool = False,
    ):
        frame_count = max(2, min(15, int(frame_count)))
        offsets = np.linspace(-1.0, 1.0, frame_count)
        frames = [self.generate_view(image, depth, float(offset), pop_out, strength) for offset in offsets]
        if len(frames) > 2:
            frames = frames + frames[-2:0:-1]
        return frames

    def lenticular(
        self,
        image: np.ndarray,
        depth: np.ndarray,
        output_width: int,
        output_height: int,
        dpi: int = 600,
        lpi: float = 60.0,
        views: int = 6,
        slant_degrees: float = 0.0,
        strength: float = 2.0,
        pop_out: bool = False,
    ) -> np.ndarray:
        output_width = max(300, min(10000, int(output_width)))
        output_height = max(200, min(10000, int(output_height)))
        dpi = max(150, min(2400, int(dpi)))
        lpi = max(10.0, min(200.0, float(lpi)))
        views = max(2, min(16, int(views)))
        image, depth = self._crop_resize_pair(image, depth, output_width, output_height)
        pitch = dpi / lpi
        yy, xx = np.indices((output_height, output_width), dtype=np.float32)
        slant = math.tan(math.radians(max(-10.0, min(10.0, slant_degrees))))
        phase = np.mod((xx + yy * slant) / pitch, 1.0)
        view_index = np.minimum(views - 1, np.floor(phase * views).astype(np.int16))
        output = np.zeros_like(image)
        for index, offset in enumerate(np.linspace(-1.0, 1.0, views)):
            view = self.generate_view(image, depth, float(offset), pop_out, strength)
            mask = view_index == index
            output[mask] = view[mask]
        return output

    def lenticular_calibration(
        self,
        dpi: int = 600,
        nominal_lpi: float = 60.0,
        span: float = 0.5,
        step: float = 0.1,
        width_in: float = 8.0,
        band_height_in: float = 0.35,
    ) -> Image.Image:
        dpi = max(150, min(2400, int(dpi)))
        step = max(0.02, min(1.0, float(step)))
        span = max(step, min(5.0, float(span)))
        values = np.arange(nominal_lpi - span, nominal_lpi + span + step / 2.0, step)
        width = int(round(width_in * dpi))
        band_h = max(80, int(round(band_height_in * dpi)))
        label_w = int(round(0.9 * dpi))
        canvas = Image.new("RGB", (width, band_h * len(values)), "white")
        draw = ImageDraw.Draw(canvas)
        font = self._font(int(0.11 * dpi), bold=True)
        for row, value in enumerate(values):
            y0 = row * band_h
            pitch = dpi / max(1.0, value)
            stripe_width = width - label_w
            x = np.arange(stripe_width, dtype=np.float32)
            stripes = (np.mod(x, pitch) < pitch / 2.0).astype(np.uint8) * 255
            band = np.repeat(stripes[np.newaxis, :], band_h, axis=0)
            rgb = np.repeat(band[:, :, np.newaxis], 3, axis=2)
            canvas.paste(Image.fromarray(rgb), (label_w, y0))
            draw.rectangle((0, y0, label_w, y0 + band_h), fill="white")
            draw.text((int(0.08 * dpi), y0 + int(0.09 * dpi)), f"{value:.2f} LPI", fill="black", font=font)
            draw.line((0, y0, width, y0), fill=(150, 150, 150), width=max(1, dpi // 300))
        return canvas


technique_generator = TechniqueGenerator()
