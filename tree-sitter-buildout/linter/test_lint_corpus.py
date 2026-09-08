"""Corpus tests for buildout-lint. Stdlib unittest — no pytest needed.

tree-sitter-buildout/linter/corpus/
    clean/    files that must lint with no findings at all
    warnings/ files that must produce at least one WARNING and no ERROR
    errors/   files that must produce at least one ERROR

Run with: python -m unittest discover -s tree-sitter-buildout/linter
"""
import importlib.util
import sys
import unittest
from pathlib import Path

try:
    from zc.buildout import lint
except ImportError:  # not installed: use the in-repo package
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
    from zc.buildout import lint

CORPUS = Path(__file__).resolve().parent / 'corpus'

have_tree_sitter = importlib.util.find_spec('tree_sitter') is not None


def corpus_files(kind):
    return sorted((CORPUS / kind).glob('*.cfg'))


@unittest.skipUnless(have_tree_sitter, 'py-tree-sitter is not installed')
class CorpusTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.parser = lint.make_parser()

    def test_clean(self):
        for path in corpus_files('clean'):
            with self.subTest(file=path.name):
                self.assertEqual(lint.lint_file(str(path), self.parser), [])

    def test_warnings(self):
        for path in corpus_files('warnings'):
            with self.subTest(file=path.name):
                findings = lint.lint_file(str(path), self.parser)
                self.assertTrue(any(f.level == 'WARNING' for f in findings))
                self.assertFalse(any(f.level == 'ERROR' for f in findings))

    def test_errors(self):
        for path in corpus_files('errors'):
            with self.subTest(file=path.name):
                findings = lint.lint_file(str(path), self.parser)
                self.assertTrue(any(f.level == 'ERROR' for f in findings))

    def test_corpus_is_not_empty(self):
        # guard against the corpus silently disappearing (e.g. moved dirs)
        self.assertGreaterEqual(len(corpus_files('clean')), 5)
        self.assertGreaterEqual(len(corpus_files('warnings')), 3)
        self.assertGreaterEqual(len(corpus_files('errors')), 3)


if __name__ == '__main__':
    unittest.main()
