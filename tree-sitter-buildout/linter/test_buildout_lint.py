"""Tests for zc.buildout.lint (the buildout-lint console script).

Stdlib unittest — no pytest needed. Skips cleanly unless py-tree-sitter
is importable. Run with:

    python -m unittest discover -s tree-sitter-buildout/linter
"""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

try:
    from zc.buildout import lint
except ImportError:  # not installed: use the in-repo package
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
    from zc.buildout import lint

have_tree_sitter = importlib.util.find_spec('tree_sitter') is not None


def levels(findings):
    return [(f.level, f.message) for f in findings]


@unittest.skipUnless(have_tree_sitter, 'py-tree-sitter is not installed')
class LintTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.parser = lint.make_parser()

    def lint_text(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'test.cfg'
            path.write_text(text)
            return lint.lint_file(str(path), self.parser)

    def test_clean_file(self):
        findings = self.lint_text(
            '[buildout]\n'
            'parts = demo\n'
            '\n'
            '[demo]\n'
            'recipe = my.recipe\n'
            'x = ${buildout:directory}\n'
        )
        self.assertEqual(findings, [])

    def test_syntax_error_is_error(self):
        findings = self.lint_text('[a\nb = 1\n')
        self.assertTrue(any(f.level == 'ERROR' for f in findings))

    def test_unsupported_hash_in_condition_is_error_via_syntax(self):
        # the reference parser rejects unescaped '#' in conditional
        # expressions
        findings = self.lint_text("[a:'#' in '#;']\nb = 1\n")
        self.assertTrue(any(f.level == 'ERROR' for f in findings))

    def test_unknown_section_reference(self):
        findings = self.lint_text('[a]\nx = ${nope:opt}\n')
        self.assertEqual(levels(findings), [
            ('WARNING', 'substitution references unknown section [nope]')])

    def test_unknown_option_reference(self):
        findings = self.lint_text('[a]\nx = 1\ny = ${a:nope}\n')
        self.assertEqual(levels(findings), [
            ('WARNING', 'substitution references unknown option a:nope')])

    def test_same_section_shorthand(self):
        findings = self.lint_text('[a]\nx = 1\ny = ${:x}\n')
        self.assertEqual(findings, [])
        findings = self.lint_text('[a]\ny = ${:x}\n')
        self.assertEqual([f.level for f in findings], ['WARNING'])

    def test_macro_reference_unknown(self):
        findings = self.lint_text('[a]\n<= nowhere\n')
        self.assertEqual([f.level for f in findings], ['WARNING'])
        findings = self.lint_text('[a]\nx = 1\n\n[b]\n<= a\n')
        self.assertEqual(findings, [])

    def test_malformed_substitution_missing_colon(self):
        findings = self.lint_text('[a]\nx = ${nocolon}\n')
        self.assertTrue(any(f.level == 'ERROR' and 'expected' in f.message
                            for f in findings))

    def test_malformed_substitution_bad_chars(self):
        findings = self.lint_text('[a]\nx = ${b+c:d}\n')
        self.assertTrue(any(f.level == 'ERROR' and 'identifiers' in f.message
                            for f in findings))

    def test_conditional_duplicate_sections_are_fine(self):
        findings = self.lint_text(
            '[versions]\n'
            'a = 1\n'
            '\n'
            '[versions:python_version >= "3.13"]\n'
            'a = 2\n'
            '\n'
            '[versions:python_version >= "3.14"]\n'
            'a = 3\n'
        )
        self.assertEqual(findings, [])

    def test_true_duplicate_section_warns(self):
        findings = self.lint_text('[a]\nx = 1\n\n[a]\ny = 2\n')
        self.assertEqual([f.level for f in findings], ['WARNING'])

    def test_environ_is_not_unknown(self):
        findings = self.lint_text('[a]\nx = ${__environ__:HOME}\n')
        self.assertEqual(findings, [])

    def test_invalid_condition_expression_warns(self):
        findings = self.lint_text('[a: this is not python $$]\nx = 1\n')
        self.assertTrue(
            any(f.level == 'WARNING' and 'conditional expression' in f.message
                for f in findings))


if __name__ == '__main__':
    unittest.main()
