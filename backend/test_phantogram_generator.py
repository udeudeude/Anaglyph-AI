import numpy as np
from phantogram_generator import calibration_ruler, fit_to_print, project_relief, render_phantogram


def main():
    h, w = 80, 120
    image = np.zeros((h, w, 3), dtype=np.uint8)
    image[:, :, 0] = np.arange(w, dtype=np.uint8)
    image[:, :, 1] = 140
    image[:, :, 2] = 220
    flat = np.zeros((h, w), dtype=np.float32)

    # Zero relief must map identically to the print plane for either eye.
    left = project_relief(image, flat, 254, 190.5, 508, 355.6, -31.5, 35)
    right = project_relief(image, flat, 254, 190.5, 508, 355.6, 31.5, 35)
    assert np.array_equal(left, image)
    assert np.array_equal(right, image)

    depth = np.tile(np.linspace(0, 1, w, dtype=np.float32), (h, 1))
    fitted_image, fitted_depth = fit_to_print(image, depth, 160, 120)
    assert fitted_image.shape == (120, 160, 3)
    assert fitted_depth.shape == (120, 160)
    assert fitted_depth.dtype == np.float32

    anaglyph, l, r = render_phantogram(image, depth, relief_mm=35)
    assert anaglyph.shape == image.shape and l.shape == image.shape and r.shape == image.shape
    assert not np.array_equal(l, r)
    assert np.all(anaglyph[:, :, 2] == l[:, :, 2])

    ruler = calibration_ruler(300)
    assert abs(ruler.width - round(120 / 25.4 * 300)) <= 1
    assert abs(ruler.height - round(28 / 25.4 * 300)) <= 1

    print('Phantogram projection tests passed')


if __name__ == '__main__':
    main()
