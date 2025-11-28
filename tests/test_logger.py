import sys
import unittest
from io import StringIO

from scriptplan.utils.logger import ANSIColor, Log, get_logger


class TestANSIColor(unittest.TestCase):
    def test_green(self):
        result = ANSIColor.green("test")
        self.assertIn("test", result)
        self.assertIn('\033[32m', result)

    def test_red(self):
        result = ANSIColor.red("test")
        self.assertIn("test", result)
        self.assertIn('\033[31m', result)

    def test_yellow(self):
        result = ANSIColor.yellow("test")
        self.assertIn("test", result)
        self.assertIn('\033[33m', result)

    def test_blue(self):
        result = ANSIColor.blue("test")
        self.assertIn("test", result)
        self.assertIn('\033[34m', result)


class TestLog(unittest.TestCase):
    def setUp(self):
        # Reset Log state before each test
        Log._level = 0
        Log._stack = []
        Log._segments = []
        Log._silent = True
        Log._progress = 0
        Log._progressMeter = ''

    def test_singleton(self):
        log1 = Log()
        log2 = Log()
        self.assertIs(log1, log2)

    def test_get_logger(self):
        log = get_logger()
        self.assertIsInstance(log, Log)

    def test_set_level(self):
        Log.set_level(5)
        self.assertEqual(Log.get_level(), 5)
        self.assertEqual(Log._level, 5)

    def test_set_segments(self):
        segments = ['segment1', 'segment2']
        Log.set_segments(segments)
        self.assertEqual(Log.get_segments(), segments)

    def test_set_silent(self):
        Log.set_silent(False)
        self.assertFalse(Log.get_silent())
        Log.set_silent(True)
        self.assertTrue(Log.get_silent())

    def test_enter_no_level(self):
        # With level 0, enter should not add to stack
        Log.set_level(0)
        Log.enter("segment", "message")
        self.assertEqual(len(Log._stack), 0)

    def test_enter_with_level(self):
        Log.set_level(5)
        Log.enter("segment1", "message1")
        self.assertIn("segment1", Log._stack)

    def test_exit_no_level(self):
        Log.set_level(0)
        Log._stack = ["segment1"]
        Log.exit("segment1")
        self.assertEqual(len(Log._stack), 1)  # Not removed when level is 0

    def test_exit_with_level(self):
        Log.set_level(5)
        Log._stack = ["segment1", "segment2"]
        Log.exit("segment1")
        self.assertNotIn("segment1", Log._stack)
        self.assertNotIn("segment2", Log._stack)

    def test_msg_no_level(self):
        Log.set_level(0)
        called = [False]
        def message_func():
            called[0] = True
            return "test"
        Log.msg(message_func)
        self.assertFalse(called[0])  # Should not be called when level is 0

    def test_status_silent(self):
        Log.set_silent(True)
        # Should not output anything
        captured = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            Log.status("test message")
        finally:
            sys.stdout = old_stdout
        self.assertEqual(captured.getvalue(), "")

    def test_status_not_silent(self):
        Log.set_silent(False)
        captured = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            Log.status("test message")
        finally:
            sys.stdout = old_stdout
        self.assertIn("test message", captured.getvalue())

    def test_progress_clamp(self):
        Log.set_silent(False)
        # Test that progress values are clamped
        Log._progressMeter = "Test"
        captured = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            Log.progress(-0.5)  # Should clamp to 0
            Log.progress(1.5)  # Should clamp to 1
        finally:
            sys.stdout = old_stdout

    def test_activity_silent(self):
        Log.set_silent(True)
        # Should not output anything
        captured = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            Log.activity()
        finally:
            sys.stdout = old_stdout
        self.assertEqual(captured.getvalue(), "")


if __name__ == '__main__':
    unittest.main()
