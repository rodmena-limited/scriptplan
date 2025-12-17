import os
import tempfile
import unittest

from scriptplan.utils.message_handler import (
    Message,
    MessageHandler,
    MessageHandlerInstance,
    MessageType,
    SourceFileInfo,
    TjException,
    TjRuntimeError,
    get_message_handler_instance,
)


class TestSourceFileInfo(unittest.TestCase):
    def test_init(self):
        sfi = SourceFileInfo("test.py", 10, 5)
        self.assertEqual(sfi.fileName, "test.py")
        self.assertEqual(sfi.lineNo, 10)
        self.assertEqual(sfi.columnNo, 5)

    def test_init_defaults(self):
        sfi = SourceFileInfo("test.py")
        self.assertEqual(sfi.fileName, "test.py")
        self.assertEqual(sfi.lineNo, 0)
        self.assertEqual(sfi.columnNo, 0)

    def test_repr(self):
        sfi = SourceFileInfo("test.py", 10, 5)
        self.assertEqual(repr(sfi), "SourceFileInfo(test.py:10:5)")


class TestMessageType(unittest.TestCase):
    def test_values(self):
        self.assertEqual(MessageType.FATAL.value, 'fatal')
        self.assertEqual(MessageType.ERROR.value, 'error')
        self.assertEqual(MessageType.CRITICAL.value, 'critical')
        self.assertEqual(MessageType.WARNING.value, 'warning')
        self.assertEqual(MessageType.INFO.value, 'info')
        self.assertEqual(MessageType.DEBUG.value, 'debug')


class TestMessage(unittest.TestCase):
    def test_init_basic(self):
        msg = Message(MessageType.ERROR, "test_id", "Test message")
        self.assertEqual(msg.type, MessageType.ERROR)
        self.assertEqual(msg.id, "test_id")
        self.assertEqual(msg.message, "Test message")
        self.assertIsNone(msg.sourceFileInfo)
        self.assertIsNone(msg.line)

    def test_init_with_source_file_info(self):
        sfi = SourceFileInfo("test.py", 10)
        msg = Message(MessageType.WARNING, "test_id", "Test warning", sfi)
        self.assertEqual(msg.sourceFileInfo, sfi)

    def test_init_with_line(self):
        msg = Message(MessageType.ERROR, "test_id", "Test error", None, "  x = 1")
        self.assertEqual(msg.line, "  x = 1")

    def test_invalid_type(self):
        with self.assertRaises(ValueError):
            Message(MessageType.CRITICAL, "test_id", "Test")

    def test_invalid_message_type(self):
        with self.assertRaises(TypeError):
            Message(MessageType.ERROR, "test_id", 123)

    def test_invalid_source_file_info_type(self):
        with self.assertRaises(TypeError):
            Message(MessageType.ERROR, "test_id", "Test", "not_sfi")

    def test_invalid_line_type(self):
        with self.assertRaises(TypeError):
            Message(MessageType.ERROR, "test_id", "Test", None, 123)

    def test_str_basic(self):
        msg = Message(MessageType.ERROR, "test_id", "Test error")
        result = str(msg)
        self.assertIn("Error:", result)
        self.assertIn("Test error", result)

    def test_str_with_source_file_info(self):
        sfi = SourceFileInfo("test.py", 10)
        msg = Message(MessageType.ERROR, "test_id", "Test error", sfi)
        result = str(msg)
        self.assertIn("test.py:10:", result)

    def test_str_with_line(self):
        msg = Message(MessageType.ERROR, "test_id", "Test error", None, "  x = 1")
        result = str(msg)
        self.assertIn("x = 1", result)

    def test_str_with_scenario(self):
        class MockScenario:
            id = "test_scenario"
        scenario = MockScenario()
        msg = Message(MessageType.WARNING, "test_id", "Test warning", None, None, None, scenario)
        result = str(msg)
        self.assertIn("scenario test_scenario", result)

    def test_to_log_basic(self):
        msg = Message(MessageType.ERROR, "test_id", "Test error")
        result = msg.to_log()
        self.assertEqual(result, "Test error")

    def test_to_log_with_source_file_info(self):
        sfi = SourceFileInfo("test.py", 10)
        msg = Message(MessageType.ERROR, "test_id", "Test error", sfi)
        result = msg.to_log()
        self.assertIn("test.py:10:", result)
        self.assertIn("Test error", result)

    def test_to_log_with_scenario(self):
        class MockScenario:
            id = "test_scenario"
        scenario = MockScenario()
        msg = Message(MessageType.WARNING, "test_id", "Test warning", None, None, None, scenario)
        result = msg.to_log()
        self.assertIn("Scenario test_scenario:", result)

    def test_source_file_info_setter(self):
        msg = Message(MessageType.ERROR, "test_id", "Test")
        sfi = SourceFileInfo("new.py", 20)
        msg.sourceFileInfo = sfi
        self.assertEqual(msg.sourceFileInfo, sfi)


class TestMessageHandlerInstance(unittest.TestCase):
    def setUp(self):
        # Reset singleton state before each test
        self.handler = MessageHandlerInstance()
        self.handler.reset()
        # Disable output for tests
        self.handler.outputLevel = 0

    def test_singleton(self):
        h1 = MessageHandlerInstance()
        h2 = MessageHandlerInstance()
        self.assertIs(h1, h2)

    def test_get_message_handler_instance(self):
        handler = get_message_handler_instance()
        self.assertIsInstance(handler, MessageHandlerInstance)

    def test_reset(self):
        self.handler.appName = "test_app"
        self.handler.logFile = "test.log"
        self.handler.reset()
        self.assertEqual(self.handler.appName, 'unknown')
        self.assertIsNone(self.handler.logFile)

    def test_clear(self):
        # Add a message first (use info to avoid exit)
        self.handler.info("test", "test message")
        self.assertGreater(len(self.handler.messages), 0)
        self.handler.clear()
        self.assertEqual(len(self.handler.messages), 0)
        self.assertEqual(self.handler.errors, 0)

    def test_output_level_setter_int(self):
        self.handler.outputLevel = 3
        self.assertEqual(self.handler.outputLevel, 3)

    def test_output_level_setter_invalid(self):
        with self.assertRaises(ValueError):
            self.handler.outputLevel = 10

    def test_output_level_setter_message_type(self):
        self.handler.outputLevel = MessageType.WARNING
        self.assertEqual(self.handler.outputLevel, 3)

    def test_log_level_setter(self):
        self.handler.logLevel = 5
        self.assertEqual(self.handler.logLevel, 5)

    def test_log_level_setter_string(self):
        self.handler.logLevel = 'warning'
        self.assertEqual(self.handler.logLevel, 3)

    def test_hide_scenario(self):
        self.handler.hideScenario = False
        self.assertFalse(self.handler.hideScenario)

    def test_abort_on_warning(self):
        self.handler.abortOnWarning = True
        self.assertTrue(self.handler.abortOnWarning)

    def test_trap_setup(self):
        self.handler.trapSetup = True
        self.assertTrue(self.handler.trapSetup)

    def test_baseline_sfi(self):
        sfi = SourceFileInfo("base.py", 100)
        self.handler.baselineSFI = sfi
        self.assertEqual(self.handler.baselineSFI, sfi)

    def test_info_message(self):
        self.handler.info("test_id", "Test info message")
        self.assertEqual(len(self.handler.messages), 1)
        self.assertEqual(self.handler.messages[0].type, MessageType.INFO)

    def test_debug_message(self):
        self.handler.debug("test_id", "Test debug message")
        self.assertEqual(len(self.handler.messages), 1)
        self.assertEqual(self.handler.messages[0].type, MessageType.DEBUG)

    def test_warning_message(self):
        self.handler.warning("test_id", "Test warning")
        self.assertEqual(len(self.handler.messages), 1)
        self.assertEqual(self.handler.messages[0].type, MessageType.WARNING)

    def test_warning_abort_on_warning(self):
        self.handler.abortOnWarning = True
        with self.assertRaises(TjException):
            self.handler.warning("test_id", "Test warning")

    def test_critical_message(self):
        self.handler.critical("test_id", "Test critical")
        self.assertEqual(len(self.handler.messages), 1)
        # Critical is displayed as ERROR
        self.assertEqual(self.handler.messages[0].type, MessageType.ERROR)
        self.assertEqual(self.handler.errors, 1)

    def test_error_with_trap_setup(self):
        self.handler.trapSetup = True
        with self.assertRaises(TjRuntimeError):
            self.handler.error("test_id", "Test error")
        self.assertEqual(self.handler.errors, 1)

    def test_fatal_raises_runtime_error(self):
        with self.assertRaises(RuntimeError):
            self.handler.fatal("test_id", "Fatal error")

    def test_to_string(self):
        self.handler.info("test1", "Info message")
        self.handler.debug("test2", "Debug message")
        result = str(self.handler)
        self.assertIn("Info message", result)
        self.assertIn("Debug message", result)

    def test_log_file(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_path = f.name

        try:
            self.handler.logFile = log_path
            self.handler.logLevel = 5
            self.handler.info("test_id", "Test log message")

            with open(log_path) as f:
                content = f.read()
            self.assertIn("Test log message", content)
            self.assertIn("info", content)
        finally:
            os.unlink(log_path)

    def test_baseline_sfi_adjusts_source_info(self):
        base_sfi = SourceFileInfo("base.py", 100)
        self.handler.baselineSFI = base_sfi

        sfi = SourceFileInfo("included.py", 10)
        self.handler.info("test_id", "Test message", sfi)

        # The source file info should be adjusted
        msg = self.handler.messages[0]
        self.assertEqual(msg.sourceFileInfo.fileName, "base.py")
        self.assertEqual(msg.sourceFileInfo.lineNo, 109)  # 10 + 100 - 1


class TestMessageHandlerMixin(unittest.TestCase):
    def setUp(self):
        # Reset singleton
        self.singleton = MessageHandlerInstance()
        self.singleton.reset()
        self.singleton.outputLevel = 0

    def test_mixin_info(self):
        class TestClass(MessageHandler):
            pass

        obj = TestClass()
        obj.info("test_id", "Test info from mixin")
        self.assertEqual(len(self.singleton.messages), 1)

    def test_mixin_warning(self):
        class TestClass(MessageHandler):
            pass

        obj = TestClass()
        obj.warning("test_id", "Test warning from mixin")
        self.assertEqual(len(self.singleton.messages), 1)
        self.assertEqual(self.singleton.messages[0].type, MessageType.WARNING)

    def test_mixin_debug(self):
        class TestClass(MessageHandler):
            pass

        obj = TestClass()
        obj.debug("test_id", "Test debug from mixin")
        self.assertEqual(len(self.singleton.messages), 1)

    def test_mixin_critical(self):
        class TestClass(MessageHandler):
            pass

        obj = TestClass()
        obj.critical("test_id", "Test critical from mixin")
        self.assertEqual(self.singleton.errors, 1)

    def test_mixin_fatal_raises(self):
        class TestClass(MessageHandler):
            pass

        obj = TestClass()
        with self.assertRaises(RuntimeError):
            obj.fatal("test_id", "Test fatal from mixin")

    def test_mixin_error_with_trap(self):
        class TestClass(MessageHandler):
            pass

        self.singleton.trapSetup = True
        obj = TestClass()
        with self.assertRaises(TjRuntimeError):
            obj.error("test_id", "Test error from mixin")


class TestExceptions(unittest.TestCase):
    def test_tj_runtime_error(self):
        with self.assertRaises(TjRuntimeError):
            raise TjRuntimeError("Test error")

    def test_tj_exception(self):
        with self.assertRaises(TjException):
            raise TjException("Test exception")

    def test_tj_runtime_error_is_runtime_error(self):
        self.assertTrue(issubclass(TjRuntimeError, RuntimeError))


if __name__ == '__main__':
    unittest.main()
