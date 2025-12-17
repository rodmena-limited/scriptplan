import unittest

from scriptplan.parser.macro_processor import MacroProcessor, preprocess_tjp, strip_shell_comments


class TestStripShellComments(unittest.TestCase):

    def test_simple_comment(self):
        text = "before # comment\nafter"
        result = strip_shell_comments(text)
        self.assertEqual(result, "before \nafter")

    def test_hash_in_string_preserved(self):
        text = 'color "#FF0000" # red color'
        result = strip_shell_comments(text)
        self.assertEqual(result, 'color "#FF0000" ')

    def test_single_quote_string(self):
        text = "color '#FF0000' # red"
        result = strip_shell_comments(text)
        self.assertEqual(result, "color '#FF0000' ")

    def test_no_comments(self):
        text = 'task "Test" { effort 5d }'
        result = strip_shell_comments(text)
        self.assertEqual(result, text)

    def test_multiple_comments(self):
        text = "line1 # c1\nline2 # c2\nline3"
        result = strip_shell_comments(text)
        self.assertEqual(result, "line1 \nline2 \nline3")


class TestMacroProcessor(unittest.TestCase):

    def test_simple_macro_definition(self):
        processor = MacroProcessor()
        content = '''
macro test_macro [
  allocate dev1
  allocate dev2
]
'''
        processor.process(content)
        self.assertIn('test_macro', processor.list_macros())
        self.assertIn('allocate dev1', processor.get_macro('test_macro'))

    def test_macro_expansion(self):
        content = '''
macro greet [
  hello world
]

task test "Test" {
  ${greet}
}
'''
        result = preprocess_tjp(content)
        self.assertIn('hello world', result)
        self.assertNotIn('${greet}', result)

    def test_multiple_macros(self):
        content = '''
macro macro1 [ content1 ]
macro macro2 [ content2 ]

use ${macro1} and ${macro2}
'''
        result = preprocess_tjp(content)
        self.assertIn('content1', result)
        self.assertIn('content2', result)

    def test_nested_brackets(self):
        processor = MacroProcessor()
        content = '''
macro nested [
  task "Test" {
    effort 5d
  }
]
'''
        processor.process(content)
        macro_content = processor.get_macro('nested')
        self.assertIn('task "Test"', macro_content)
        self.assertIn('effort 5d', macro_content)

    def test_builtin_projectstart(self):
        content = '''
project test "Test" 2024-01-15 +3m {
}
start ${projectstart}
'''
        result = preprocess_tjp(content)
        self.assertIn('2024-01-15', result)
        self.assertNotIn('${projectstart}', result)

    def test_builtin_projectend(self):
        content = '''
project test "Test" 2024-01-15 +3m {
}
end ${projectend}
'''
        result = preprocess_tjp(content)
        # 2024-01-15 + 3 months = 2024-04-15
        self.assertIn('2024-04-15', result)
        self.assertNotIn('${projectend}', result)

    def test_builtin_now(self):
        content = '''
project test "Test" 2024-01-15 +3m {
  now 2024-02-01
}
date ${now}
'''
        result = preprocess_tjp(content)
        self.assertIn('2024-02-01', result)
        self.assertNotIn('${now}', result)

    def test_macro_not_in_output(self):
        content = '''
macro removed [
  this content is removed from definition site
]

after definition
'''
        result = preprocess_tjp(content)
        # Macro definition should be removed from output
        self.assertNotIn('this content is removed', result.split('after definition')[0])

    def test_multiline_macro(self):
        content = '''
macro allocate_team [
  allocate dev1 { mandatory }
  allocate dev2 { mandatory }
  allocate tester { alternative dev3 }
]

task implementation "Implementation" {
  ${allocate_team}
  effort 100d
}
'''
        result = preprocess_tjp(content)
        self.assertIn('allocate dev1 { mandatory }', result)
        self.assertIn('allocate dev2 { mandatory }', result)
        self.assertIn('allocate tester { alternative dev3 }', result)

    def test_empty_content(self):
        result = preprocess_tjp('')
        self.assertEqual(result, '')

    def test_no_macros(self):
        content = '''
project test "Test" 2024-01-15 +3m {
  timezone "UTC"
}

task foo "Foo" {
  effort 5d
}
'''
        result = preprocess_tjp(content)
        # Should be essentially unchanged
        self.assertIn('project test', result)
        self.assertIn('task foo', result)

    def test_unknown_macro_preserved(self):
        content = '${unknown_macro}'
        result = preprocess_tjp(content)
        # Unknown macros should be preserved (parser will handle errors)
        self.assertIn('${unknown_macro}', result)

    def test_macro_in_string_handling(self):
        # Macros should still be expanded even in strings
        # (TJP doesn't distinguish - macro expansion is pure text substitution)
        content = '''
macro version [1.0]
project test "Version ${version}" 2024-01-15 +3m {
}
'''
        result = preprocess_tjp(content)
        self.assertIn('Version 1.0', result)


class TestPreprocessTjp(unittest.TestCase):

    def test_function_exists(self):
        from scriptplan.parser.macro_processor import preprocess_tjp
        self.assertTrue(callable(preprocess_tjp))

    def test_returns_string(self):
        result = preprocess_tjp('content')
        self.assertIsInstance(result, str)


if __name__ == '__main__':
    unittest.main()
