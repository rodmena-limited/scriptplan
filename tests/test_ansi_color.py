"""The terminal colours used to mark diagnostics by severity."""

import unittest

from scriptplan.utils.logger import ANSIColor


class TestANSIColor(unittest.TestCase):
    def test_each_colour_wraps_the_text_and_resets_after_it(self) -> None:
        for paint in (ANSIColor.green, ANSIColor.red, ANSIColor.yellow, ANSIColor.blue):
            painted = paint("hello")
            self.assertIn("hello", painted)
            self.assertTrue(painted.endswith("\033[0m"), f"{paint.__name__} must reset")
            self.assertTrue(painted.startswith("\033["), f"{paint.__name__} must set a colour")

    def test_colours_differ_from_one_another(self) -> None:
        painted = {
            paint("x") for paint in (ANSIColor.green, ANSIColor.red, ANSIColor.yellow, ANSIColor.blue)
        }
        self.assertEqual(len(painted), 4, "each severity must be visually distinct")


if __name__ == "__main__":
    unittest.main()
