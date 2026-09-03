import numpy as np

from depth_sources import align_depth, normalise_depth
from stereo_formats import compatibility_stereo, make_anaglyph
from technique_generator import technique_generator


def sample_data(width=96, height=64):
    x = np.linspace(0, 255, width, dtype=np.uint8)
    y = np.linspace(0, 255, height, dtype=np.uint8)[:, None]
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[:, :, 0] = x
    image[:, :, 1] = y
    image[:, :, 2] = 180
    depth = np.tile(np.linspace(0.0, 1.0, width, dtype=np.float32), (height, 1))
    return image, depth


def main():
    image, depth = sample_data()

    view = technique_generator.generate_view(image, depth, 0.5, False, 2.0)
    assert view.shape == image.shape and view.dtype == np.uint8

    chroma = technique_generator.chromadepth(image, depth, 0.9, False)
    assert chroma.shape == image.shape and chroma.dtype == np.uint8

    red_cyan = make_anaglyph(image, view, 'red-cyan', 'full')
    red_green = make_anaglyph(image, view, 'red-green', 'half')
    red_blue = make_anaglyph(image, view, 'red-blue', 'gray')
    assert red_cyan.shape == image.shape
    assert np.all(red_green[:, :, 0] == 0)
    assert np.all(red_blue[:, :, 1] == 0)

    assert compatibility_stereo(image, view, 'topbottom').shape == (image.shape[0] * 2, image.shape[1], 3)
    assert compatibility_stereo(image, view, 'halfsbs').shape == image.shape
    assert compatibility_stereo(image, view, 'rowinterlaced').shape == image.shape
    assert compatibility_stereo(image, view, 'columninterlaced').shape == image.shape
    assert compatibility_stereo(image, view, 'checkerboard').shape == image.shape

    depth_small = np.arange(24, dtype=np.uint16).reshape(4, 6)
    normalised = normalise_depth(depth_small)
    assert normalised.dtype == np.float32 and normalised.min() >= 0 and normalised.max() <= 1
    for mode in ('crop', 'fit', 'stretch'):
        aligned = align_depth(normalised, image.shape[1], image.shape[0], mode)
        assert aligned.shape == image.shape[:2]

    cardboard = technique_generator.cardboard(view, view, 640, 360, 121, 63, 0.92)
    assert cardboard.shape == (360, 640, 3)

    card = technique_generator.stereoscope_card(view, view, dpi=72)
    assert card.ndim == 3 and card.shape[2] == 3

    parallel = technique_generator.autostereogram(depth, style='random', separation_percent=10, depth_percent=2, dot_size=2, viewing='parallel')
    cross = technique_generator.autostereogram(depth, style='random', separation_percent=10, depth_percent=2, dot_size=2, viewing='cross')
    assert parallel.shape == image.shape
    assert cross.shape == image.shape
    assert not np.array_equal(parallel, cross)

    guided = technique_generator.autostereogram(depth, style='random', separation_percent=10, depth_percent=2, dot_size=2, viewing='parallel-guides')
    assert guided.shape[0] > image.shape[0] and guided.shape[1:] == image.shape[1:]

    patterned = technique_generator.autostereogram(depth, style='pattern', separation_percent=10, depth_percent=2)
    assert patterned.shape == image.shape
    assert np.unique(patterned.reshape(-1, 3), axis=0).shape[0] > 2

    frames = technique_generator.wiggle_frames(image, depth, frame_count=5, strength=2.0)
    assert len(frames) == 8
    assert all(frame.shape == image.shape for frame in frames)

    lenticular = technique_generator.lenticular(image, depth, 300, 200, dpi=150, lpi=60, views=3)
    assert lenticular.shape == (200, 300, 3)

    calibration = technique_generator.lenticular_calibration(dpi=150, nominal_lpi=60, span=0.2, step=0.1, width_in=2)
    assert calibration.width == 300 and calibration.height > 0

    print('Technique renderer smoke tests passed')


if __name__ == '__main__':
    main()
