import unittest
import numpy as np
from dreamtalk.pipeline.face_hair import sample_hair_colour


class HairColorTests(unittest.TestCase):
    def test_middle_grey_is_linear_not_encoded(self):
        image = np.full((2, 2, 3), 128, np.uint8)
        result = sample_hair_colour(image, np.ones((2, 2), np.uint8), 1)
        np.testing.assert_allclose(result, [0.21586] * 3, atol=1e-5)

    def test_black_is_not_brightened(self):
        image = np.zeros((2, 2, 3), np.uint8)
        self.assertEqual(sample_hair_colour(image, np.ones((2, 2)), 1), (0, 0, 0))

    def test_only_segmented_hair_contributes(self):
        image = np.full((2, 2, 3), 255, np.uint8)
        image[0, 0] = [10, 20, 30]
        mask = np.zeros((2, 2), np.uint8)
        mask[0, 0] = 1
        result = sample_hair_colour(image, mask, 1)
        self.assertLess(result[2], 0.014)
        self.assertLess(result[0], result[1])


if __name__ == "__main__":
    unittest.main()
