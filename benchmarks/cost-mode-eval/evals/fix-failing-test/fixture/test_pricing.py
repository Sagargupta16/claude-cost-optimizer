import unittest

from pricing import apply_discount


class ApplyDiscountTest(unittest.TestCase):
    def test_ten_percent_off(self) -> None:
        self.assertEqual(apply_discount(200.0, 10), 180.0)

    def test_zero_percent(self) -> None:
        self.assertEqual(apply_discount(49.99, 0), 49.99)

    def test_full_discount(self) -> None:
        self.assertEqual(apply_discount(80.0, 100), 0.0)


if __name__ == "__main__":
    unittest.main()
