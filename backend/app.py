from flask import Flask, jsonify, request, session
from flask_cors import CORS
import uuid
import os
from PIL import Image
import cv2
import time
import numpy as np

from depth_map_generator import depth_map_generator
from anaglyph_generator import anaglyph_generator
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from werkzeug.utils import send_from_directory

app = Flask(__name__)
CORS(app, supports_credentials=True)

load_dotenv()
host = os.getenv("FLASK_HOST", "0.0.0.0")
port = int(os.getenv("FLASK_PORT", 8000))
app.secret_key = 'super secret key'

MAX_DIMENSION = 1500
KERNEL_WIDTH = 15
SESSION_DATA_FOLDER = 'resources/session_data'
os.makedirs(SESSION_DATA_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {
    'bmp', 'dib', 'jpeg', 'jpg', 'jpe', 'jp2', 'png', 'webp',
    'pbm', 'pgm', 'ppm', 'pxm', 'pnm', 'sr', 'ras', 'tiff', 'tif',
    'exr', 'hdr', 'pic'
}

depth_map_resize_dimension = 518
RANDOM_IMAGES_FOLDER = 'resources/random_images'
num_random_images = len([
    name for name in os.listdir(RANDOM_IMAGES_FOLDER)
    if os.path.isfile(os.path.join(RANDOM_IMAGES_FOLDER, name))
])
RANDOM_IMAGES_DEPTH_MAPS_GREYSCALE_FOLDER = 'resources/random_images_depth_maps_greyscale'


@app.route('/')
def hello_world():
    return 'Hello World!!'


@app.before_request
def assign_session_id():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())


def clear_old_session_files():
    current_time = time.time()
    session_files_cleared = 0
    for filename in os.listdir(SESSION_DATA_FOLDER):
        path = os.path.join(SESSION_DATA_FOLDER, filename)
        if current_time - os.path.getmtime(path) > 60 * 60:
            os.remove(path)
            session_files_cleared += 1
    print(f"Session files cleared: {session_files_cleared}")


clean_up_scheduler = BackgroundScheduler()
clean_up_scheduler.add_job(clear_old_session_files, 'interval', hours=1)
clean_up_scheduler.start()


@app.route('/image', methods=['POST'])
def upload_image():
    session['random_image'] = False

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    image = request.files['file']
    if image.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if image.filename.split('.')[-1].lower() not in ALLOWED_EXTENSIONS:
        return jsonify({'error': 'Invalid file type'}), 400

    try:
        pillow_image = Image.open(image)
        exif_data = pillow_image._getexif()
        if exif_data is not None:
            orientation = exif_data.get(274)
            if orientation == 3:
                pillow_image = pillow_image.rotate(180, expand=True)
            elif orientation == 6:
                pillow_image = pillow_image.rotate(270, expand=True)
            elif orientation == 8:
                pillow_image = pillow_image.rotate(90, expand=True)

        pillow_image = pillow_image.convert('RGB')
        if pillow_image.width > MAX_DIMENSION or pillow_image.height > MAX_DIMENSION:
            pillow_image.thumbnail((MAX_DIMENSION, MAX_DIMENSION))

        image_name = f"{session['session_id']}_image.jpg"
        pillow_image.save(os.path.join(SESSION_DATA_FOLDER, image_name), format='JPEG')
        return jsonify({"Success": "Image uploaded successfully"}), 200
    except Exception as e:
        return jsonify({'error': str(e) + " Note: transparent background not allowed"}), 400


@app.route('/random_image', methods=['GET'])
def get_random_image():
    random_image_index = np.random.randint(0, num_random_images)
    random_image_name = f"image_{random_image_index}.jpg"
    random_image_path = os.path.join(RANDOM_IMAGES_FOLDER, random_image_name)

    session_image = Image.open(random_image_path)
    session_image_name = f"{session['session_id']}_image.jpg"
    session_image.save(os.path.join(SESSION_DATA_FOLDER, session_image_name), format='JPEG')

    session['random_image'] = True
    session['random_image_index'] = int(random_image_index)
    return send_from_directory(RANDOM_IMAGES_FOLDER, random_image_name, request.environ)


@app.route('/depth-map', methods=['GET'])
def get_depth_map():
    depth_map_coloured_name = f"{session['session_id']}_depth_map_coloured.jpg"
    process_depth_maps()
    return send_from_directory(SESSION_DATA_FOLDER, depth_map_coloured_name, request.environ)


def process_depth_maps():
    try:
        image_name = f"{session['session_id']}_image.jpg"
        image_path = os.path.join(SESSION_DATA_FOLDER, image_name)
        image = cv2.imread(image_path)
        if image is None:
            raise FileNotFoundError(f"Image not found at path: {image_path}")

        if session.get('random_image', False):
            random_image_index = session['random_image_index']
            depth_map_greyscaled_name = f"depth_map_greyscale_{random_image_index}.jpg"
            depth_map_greyscaled_path = os.path.join(
                RANDOM_IMAGES_DEPTH_MAPS_GREYSCALE_FOLDER,
                depth_map_greyscaled_name
            )
            depth_map_greyscaled = cv2.imread(depth_map_greyscaled_path, cv2.IMREAD_GRAYSCALE)
            depth_map = depth_map_greyscaled / 255.0
        else:
            depth_map = depth_map_generator.generate_depth_map_performant(
                image,
                depth_map_resize_dimension,
                depth_map_resize_dimension
            )

        depth_map_coloured = depth_map_generator.colour_depth_map(depth_map)
        depth_map_coloured_name = f"{session['session_id']}_depth_map_coloured.jpg"
        cv2.imwrite(os.path.join(SESSION_DATA_FOLDER, depth_map_coloured_name), depth_map_coloured)

        depth_map_blurred = depth_map_generator.blur_depth_map(depth_map, KERNEL_WIDTH)
        depth_map_name = f"{session['session_id']}_depth_map.npy"
        np.save(os.path.join(SESSION_DATA_FOLDER, depth_map_name), depth_map_blurred)
    except Exception as e:
        print(f"Error processing depth maps: {e}")


def generate_stereo_pair():
    depth_map_name = f"{session['session_id']}_depth_map.npy"
    depth_map = np.load(os.path.join(SESSION_DATA_FOLDER, depth_map_name))

    image_name = f"{session['session_id']}_image.jpg"
    image_path = os.path.join(SESSION_DATA_FOLDER, image_name)
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Image not found at path: {image_path}")

    pop_out = request.args.get("pop_out", default="false").lower() == "true"
    max_disparity_percentage = float(request.args.get("max_disparity_percentage", default=2))
    return anaglyph_generator.generate_stereo_images(
        image, depth_map, pop_out, max_disparity_percentage
    )


@app.route('/anaglyph', methods=['GET'])
def get_anaglyph():
    anaglyph_name = f"{session['session_id']}_anaglyph.jpg"
    try:
        left_image, right_image = generate_stereo_pair()
        optimised = request.args.get("optimised_RR_anaglyph", default="false").lower() == "true"
        if optimised:
            anaglyph = anaglyph_generator.generate_optimised_RR_anaglyph(left_image, right_image)
        else:
            anaglyph = anaglyph_generator.generate_pure_anaglyph(left_image, right_image)
        cv2.imwrite(os.path.join(SESSION_DATA_FOLDER, anaglyph_name), anaglyph)
    except Exception as e:
        return jsonify({"Error generating anaglyph": str(e)}), 400

    return send_from_directory(SESSION_DATA_FOLDER, anaglyph_name, request.environ)


@app.route('/stereo-pair', methods=['GET'])
def get_stereo_pair():
    """Return a side-by-side stereo JPEG in parallel or cross-eyed ordering."""
    mode = request.args.get("mode", default="parallel").lower()
    if mode not in ('parallel', 'cross'):
        return jsonify({'error': 'mode must be parallel or cross'}), 400

    try:
        left_image, right_image = generate_stereo_pair()

        # Parallel (wall-eyed): left-eye view on left, right-eye view on right.
        # Cross-eyed: swap the views so each crossed eye sees its intended image.
        if mode == 'parallel':
            stereo_pair = np.hstack((left_image, right_image))
        else:
            stereo_pair = np.hstack((right_image, left_image))

        pair_name = f"{session['session_id']}_{mode}_stereo.jpg"
        cv2.imwrite(os.path.join(SESSION_DATA_FOLDER, pair_name), stereo_pair)
        return send_from_directory(SESSION_DATA_FOLDER, pair_name, request.environ)
    except Exception as e:
        return jsonify({"Error generating stereo pair": str(e)}), 400


if __name__ == '__main__':
    app.run(debug=True, host=host, port=port)
