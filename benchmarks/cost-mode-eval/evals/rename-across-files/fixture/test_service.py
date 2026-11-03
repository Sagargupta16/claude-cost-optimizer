import unittest

from service import greeting
from users import fetch_user


class ServiceTest(unittest.TestCase):
    def test_returns_the_record(self) -> None:
        self.assertEqual(fetch_user(7)["id"], 7)

    def test_greeting_uses_the_name(self) -> None:
        self.assertEqual(greeting(3), "Hello, user3")


if __name__ == "__main__":
    unittest.main()
