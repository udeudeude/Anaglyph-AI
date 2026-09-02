from flask import Flask, jsonify, request, session, send_file, send_from_directory
from flask_cors import CORS
import uuid
import os
import io
import json
import time
from PIL import Image, ImageOps
import cv2
import numpy as np

from depth_map_generator import depth_map_generator
from anaglyph_generator import anaglyph_generator
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app, supports_credentials=True)

load_dotenv()
host = os.getenv("FLASK_HOST", "0.0.0.0")
port = int(os.getenv("FLASK_PORT", 8000))
app.secret_key = os.getenv("FLASK_SECRET_KEY", "local-anaglyph-and-friends")

KERNEL_WIDTH = 15
PREVIEW_MAX_DIMENSION = 1600
SESSION_DATA_FOLDER = "resources/session_data"
os.makedirs(SESSION_DATA_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {
    "bmp", "dib", "jpeg", "jpg", "jpe", "jp2", "png", "webp",
    "pbm", "pgm", "ppm", "pxm", "pnm", "sr", "ras", "tiff", "tif",
    "exr", "hdr", "pic"
}


@app.route("/")
def hello_world():
    return "Anaglyph & Friends backend"


@app.before_request
def assign_session_id():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())


def session_path(suffix: str) -> str:
    return os.path.join(SESSION_DATA_FOLDER, f"{session['session_id']}_{suffix}")


def clear_session_products():
    prefix = f"{session['session_id']}_"
    for filename in os.listdir(SESSION_DATA_FOLDER):
        if filename.startswith(prefix):
            try:
                os.remove(os.path.join(SESSION_DATA_FOLDER, filename))
            except FileNotFoundError:
                pass


def clear_old_session_files():
    current_time = time.time()
    session_files_cleared = 0
    for filename in os.listdir(SESSION_DATA_FOLDER):
        path = os.path.join(SESSION_DATA_FOLDER, filename)
        if os.path.isfile(path) and current_time - os.path.getmtime(path) > 60 * 60:
            os.remove(path)
            session_files_cleared += 1
    print(f"Session files cleared: {session_files_cleared}")


clean_up_scheduler = BackgroundScheduler()
clean_up_scheduler.add_job(clear_old_session_files, "interval", hours=1)
clean_up_scheduler.start()


def parse_render_parameters():
    pop_out = request.args.get("pop_out", default="false").lower() == "true"
    max_disparity_percentage = float(request.args.get("max_disparity_percentage", default=2))
    max_disparity_percentage = max(0.0, min(6.0, max_disparity_percentage))
    return pop_out, max_disparity_percentage


def resize_image_and_depth(image, depth_map, max_dimension):
    height, width = image.shape[:2]
    scale = min(1.0, max_dimension / max(height, width))
    if scale >= 1.0:
        return image, depth_map
    new_width = max(1, int(round(width * scale)))
    new_height = max(1, int(round(height * scale)))
    image_resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
    depth_resized = cv2.resize(depth_map.astype(np.float32), (new_width, new_height), interpolation=cv2.INTER_CUBIC)
    return image_resized, np.clip(depth_resized, 0.0, 1.0).astype(np.float32)


@app.route("/image", methods=["POST"])
def upload_image():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    image = request.files["file"]
    if image.filename == "":
        return jsonify({"error": "No selected file"}), 400
    extension = image.filename.rsplit(".", 1)[-1].lower() if "." in image.filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        return jsonify({"error": "Invalid file type"}), 400

    try:
        pillow_image = Image.open(image)
        pillow_image = ImageOps.exif_transpose(pillow_image).convert("RGB")
        clear_session_products()
        original_path = session_path("image.png")
        pillow_image.save(original_path, format="PNG", optimize=False)
        return jsonify({
            "success": True,
            "width": pillow_image.width,
            "height": pillow_image.height,
            "full_resolution": True,
        }), 200
    except Exception as e:
        return jsonify({"error": str(e) + " Note: transparent background not allowed"}), 400


def ensure_depth_maps():
    depth_path = session_path("depth_map.npy")
    coloured_path = session_path("depth_map_coloured.jpg")
    gray16_path = session_path("depth_map_gray16.png")
    if os.path.exists(depth_path) and os.path.exists(coloured_path) and os.path.exists(gray16_path):
        return

    image_path = session_path("image.png")
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError("No uploaded source image is available")

    depth_map = depth_map_generator.generate_depth_map(image)
    depth_map_blurred = np.clip(depth_map_generator.blur_depth_map(depth_map, KERNEL_WIDTH), 0.0, 1.0).astype(np.float32)
    np.save(depth_path, depth_map_blurred, allow_pickle=False)

    coloured = depth_map_generator.colour_depth_map(depth_map_blurred)
    coloured_preview, _ = resize_image_and_depth(coloured, depth_map_blurred, PREVIEW_MAX_DIMENSION)
    cv2.imwrite(coloured_path, coloured_preview, [int(cv2.IMWRITE_JPEG_QUALITY), 92])

    gray16 = np.round(depth_map_blurred * 65535.0).astype(np.uint16)
    cv2.imwrite(gray16_path, gray16)


@app.route("/depth-map", methods=["GET"])
def get_depth_map():
    try:
        ensure_depth_maps()
        return send_from_directory(SESSION_DATA_FOLDER, os.path.basename(session_path("depth_map_coloured.jpg")), request.environ)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/depth-map/download", methods=["GET"])
def download_depth_map():
    try:
        ensure_depth_maps()
        kind = request.args.get("kind", "gray16").lower()
        if kind == "gray16":
            return send_file(session_path("depth_map_gray16.png"), as_attachment=True, download_name="depth-map-16bit.png", mimetype="image/png")
        if kind == "color":
            return send_file(session_path("depth_map_coloured.jpg"), as_attachment=True, download_name="depth-map-color.jpg", mimetype="image/jpeg")
        if kind == "npy":
            return send_file(session_path("depth_map.npy"), as_attachment=True, download_name="depth-map-float32.npy", mimetype="application/octet-stream")
        return jsonify({"error": "kind must be gray16, color, or npy"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400


def cache_paths(scope):
    if scope not in ("preview", "full"):
        raise ValueError("scope must be preview or full")
    return {
        "left": session_path(f"{scope}_left.png"),
        "right": session_path(f"{scope}_right.png"),
        "meta": session_path(f"{scope}_stereo.json"),
    }


def cache_matches(meta_path, pop_out, max_disparity_percentage):
    try:
        with open(meta_path, "r", encoding="utf-8") as handle:
            meta = json.load(handle)
        return (
            bool(meta.get("pop_out")) == bool(pop_out)
            and abs(float(meta.get("max_disparity_percentage")) - float(max_disparity_percentage)) < 1e-9
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def ensure_stereo_pair(scope, pop_out, max_disparity_percentage):
    ensure_depth_maps()
    paths = cache_paths(scope)
    if os.path.exists(paths["left"]) and os.path.exists(paths["right"]) and cache_matches(paths["meta"], pop_out, max_disparity_percentage):
        return paths

    image = cv2.imread(session_path("image.png"))
    depth_map = np.load(session_path("depth_map.npy"), allow_pickle=False).astype(np.float32)
    if image is None:
        raise FileNotFoundError("No uploaded source image is available")

    if scope == "preview":
        image, depth_map = resize_image_and_depth(image, depth_map, PREVIEW_MAX_DIMENSION)

    left_image, right_image = anaglyph_generator.generate_stereo_images(
        image,
        depth_map,
        pop_out,
        max_disparity_percentage,
    )
    cv2.imwrite(paths["left"], left_image)
    cv2.imwrite(paths["right"], right_image)
    with open(paths["meta"], "w", encoding="utf-8") as handle:
        json.dump({
            "pop_out": pop_out,
            "max_disparity_percentage": max_disparity_percentage,
            "width": int(image.shape[1]),
            "height": int(image.shape[0]),
        }, handle)
    return paths


@app.route("/render", methods=["GET"])
def render_preview_stereo():
    try:
        pop_out, strength = parse_render_parameters()
        paths = ensure_stereo_pair("preview", pop_out, strength)
        with open(paths["meta"], "r", encoding="utf-8") as handle:
            meta = json.load(handle)
        return jsonify({"success": True, "scope": "preview", **meta})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/prepare-full", methods=["GET"])
def prepare_full_stereo():
    try:
        pop_out, strength = parse_render_parameters()
        paths = ensure_stereo_pair("full", pop_out, strength)
        with open(paths["meta"], "r", encoding="utf-8") as handle:
            meta = json.load(handle)
        return jsonify({"success": True, "scope": "full", **meta})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


def build_output(kind, scope, pop_out, strength, optimised):
    paths = ensure_stereo_pair(scope, pop_out, strength)
    left_image = cv2.imread(paths["left"])
    right_image = cv2.imread(paths["right"])
    if left_image is None or right_image is None:
        raise FileNotFoundError("Stereo render cache is unavailable")

    if kind == "left":
        return left_image
    if kind == "right":
        return right_image
    if kind == "parallel":
        return np.hstack((left_image, right_image))
    if kind == "cross":
        return np.hstack((right_image, left_image))
    if kind == "anaglyph":
        if optimised:
            return anaglyph_generator.generate_optimised_RR_anaglyph(left_image, right_image)
        return anaglyph_generator.generate_pure_anaglyph(left_image, right_image)
    raise ValueError("kind must be anaglyph, parallel, cross, left, or right")


@app.route("/output/<kind>", methods=["GET"])
def get_output(kind):
    try:
        scope = request.args.get("scope", "preview").lower()
        pop_out, strength = parse_render_parameters()
        optimised = request.args.get("optimised_RR_anaglyph", default="false").lower() == "true"
        output_format = request.args.get("format", "jpeg").lower()
        quality = int(request.args.get("quality", 95))
        quality = max(40, min(100, quality))
        download = request.args.get("download", "false").lower() == "true"

        if output_format not in ("jpeg", "jpg", "png"):
            return jsonify({"error": "format must be jpeg or png"}), 400

        output = build_output(kind.lower(), scope, pop_out, strength, optimised)
        if output_format in ("jpeg", "jpg"):
            ok, encoded = cv2.imencode(".jpg", output, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
            mimetype = "image/jpeg"
            extension = "jpg"
        else:
            ok, encoded = cv2.imencode(".png", output)
            mimetype = "image/png"
            extension = "png"
        if not ok:
            raise RuntimeError("Could not encode output image")

        names = {
            "anaglyph": "red-cyan-anaglyph",
            "parallel": "parallel-stereo",
            "cross": "cross-eyed-stereo",
            "left": "left-eye",
            "right": "right-eye",
        }
        filename = f"{names.get(kind.lower(), kind.lower())}.{extension}"
        return send_file(
            io.BytesIO(encoded.tobytes()),
            mimetype=mimetype,
            as_attachment=download,
            download_name=filename,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Backwards-compatible endpoints retained for old frontends/bookmarks.
@app.route("/anaglyph", methods=["GET"])
def legacy_anaglyph():
    return get_output("anaglyph")


@app.route("/stereo-pair", methods=["GET"])
def legacy_stereo_pair():
    mode = request.args.get("mode", "parallel").lower()
    if mode not in ("parallel", "cross"):
        return jsonify({"error": "mode must be parallel or cross"}), 400
    return get_output(mode)


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, host=host, port=port)
