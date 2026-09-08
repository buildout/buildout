"""buildout-lint: lint zc.buildout configuration files via a tree-sitter CST.

Install with the ``linter`` extra and use the console script::

    pip install zc.buildout[linter]
    buildout-lint FILE [FILE ...]

Exit status: 1 if any ERROR-level finding, 0 otherwise.

Checks, in order of severity:

- ERROR   syntax errors (tree-sitter ERROR or MISSING nodes) — the reference
          parser (zc.buildout.configparser) would raise ParsingError or
          MissingSectionHeaderError on these
- ERROR   malformed substitution (${...} must be ${section:option} or
          ${:option}; identifiers may only contain [-a-zA-Z0-9 ._])
- WARNING unresolved references: ${section:option} where the section or
          option does not exist in this file, ${:option} shorthand with no
          such option in the current section, '<=' macro referencing an
          unknown section
- WARNING duplicate section name (the reference parser merges them;
          conditional variants of one section are exempt)
- WARNING conditional header expression is neither a PEP 508 marker nor
          valid Python syntax

Note: resolution is file-local only. Options injected by recipes, macros
('<='), 'extends' layering or '[buildout] versions' can produce false
positives — this is a linter, not the parser.

The grammar (tree-sitter-buildout/ in the source distribution) is generated
to C; the generated ``parser.c`` is vendored under ``zc/buildout/grammar/``
and compiled with the system C compiler (override with the ``CC``
environment variable) into a cache in the system temp dir on first use.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

GRAMMAR_DIR = Path(__file__).resolve().parent / 'grammar'
PARSER_C = GRAMMAR_DIR / 'parser.c'

_SUB_SHAPE = re.compile(r'^\$\{([-a-zA-Z0-9 ._]*):([-a-zA-Z0-9 ._]+)\}$')
_SUB_ANY = re.compile(r'^\$\{[^}]*\}$')


def build_parser_lib():
    """Compile the vendored generated parser with the system C compiler.

    Cached under the system temp dir, keyed by parser.c's mtime.
    """
    stamp = str(int(PARSER_C.stat().st_mtime))
    lib = Path(tempfile.gettempdir()) / f'tree-sitter-buildout-{stamp}.so'
    if not lib.exists():
        cc = os.environ.get('CC', 'cc')
        try:
            subprocess.run(
                [cc, '-O2', '-shared', '-fPIC',
                 '-o', str(lib), str(PARSER_C), '-I', str(PARSER_C.parent)],
                check=True)
        except FileNotFoundError:
            raise SystemExit(
                f'buildout-lint: C compiler {cc!r} not found. '
                'Install one (e.g. gcc/clang) or set the CC environment '
                'variable.')
        except subprocess.CalledProcessError as e:
            raise SystemExit(
                f'buildout-lint: failed to compile {PARSER_C}: {e}')
    return lib


def load_language():
    try:
        from tree_sitter import Language
    except ImportError:
        raise SystemExit(
            'buildout-lint requires the py-tree-sitter package: '
            'pip install zc.buildout[linter]')
    import ctypes
    lib_path = build_parser_lib()
    dll = ctypes.CDLL(str(lib_path))
    dll.tree_sitter_buildout.restype = ctypes.c_void_p
    import warnings
    with warnings.catch_warnings():
        # constructing a Language from a raw pointer is deprecated but
        # still the only way with py-tree-sitter 0.23-0.26
        warnings.simplefilter('ignore', DeprecationWarning)
        return Language(dll.tree_sitter_buildout())


def make_parser(language=None):
    """Return a tree_sitter.Parser for the buildout grammar.

    Works across py-tree-sitter 0.23 (Parser() + set_language) and
    0.24+ (Parser(language)).
    """
    from tree_sitter import Parser
    if language is None:
        language = load_language()
    try:
        return Parser(language)
    except TypeError:
        parser = Parser()
        parser.set_language(language)
        return parser


class Finding:
    def __init__(self, level, path, line, col, message):
        self.level = level
        self.path = path
        self.line = line
        self.col = col
        self.message = message

    def __str__(self):
        return f"{self.path}:{self.line}:{self.col}: {self.level}: {self.message}"


def _text(node):
    return node.text.decode('utf-8', 'replace')


def lint_file(path, parser):
    src = Path(path).read_bytes()
    tree = parser.parse(src)
    findings = []

    def add(level, node, message):
        findings.append(Finding(level, path, node.start_point[0] + 1,
                                node.start_point[1] + 1, message))

    def walk_errors(node):
        if node.type == 'ERROR':
            add('ERROR', node,
                'syntax error near ' + repr(_text(node)[:40]))
            return  # do not descend; one error per region is enough
        if node.is_missing:
            add('ERROR', node, f'missing {node.type}')
            return
        for child in node.children:
            walk_errors(child)

    walk_errors(tree.root_node)

    # collect sections and their option names for reference checks
    sections = {}  # name -> set(option names)
    seen_sections = set()
    section_nodes = []  # (section_node, name) in order

    def section_name_of(header):
        for child in header.children:
            if child.type == 'section_name':
                return _text(child)
        return None

    def option_key(option):
        """Mirror configparser.parse: fold a trailing +/- into the key."""
        name = op = None
        for child in option.children:
            if child.type == 'option_name':
                name = _text(child)
            elif child.type == 'assignment':
                op = _text(child)
        if name is None:
            return None
        name = name.rstrip()
        if op:
            m = re.match(r'^[ \t]*([-+]?)[ \t]*=', op)
            if m and m.group(1):
                name = f'{name} {m.group(1)}'
        return name

    for section in (n for n in tree.root_node.children if n.type == 'section'):
        name = None
        condition = None
        for child in section.children:
            if child.type == 'section_header':
                name = section_name_of(child)
                for grandchild in child.children:
                    if grandchild.type == 'condition':
                        condition = _text(grandchild)
            elif child.type == 'option' and name is not None:
                key = option_key(child)
                if key is not None:
                    sections.setdefault(name, set()).add(key)
        if name is not None:
            # conditional variants of one section ([versions:py>=3.13],
            # [versions:py>=3.14]) are an intended pattern, not duplication
            if (name, condition) in seen_sections:
                add('WARNING', section.children[0],
                    f'duplicate section [{name}] (merged by the reference parser)')
            seen_sections.add((name, condition))
            sections.setdefault(name, set())
            section_nodes.append((section, name))

    def check_references():
        for section, sname in section_nodes:
            for node in _iter(section):
                if node.type == 'substitution':
                    _check_substitution(node, sname)
                elif node.type == 'option':
                    key = option_key(node)
                    if key == '<':
                        for child in node.children:
                            if child.type == 'value':
                                for ref in _text(child).split():
                                    if ref not in sections:
                                        add('WARNING', child,
                                            f'macro reference <= {ref} has no '
                                            f'matching section in this file')
                elif node.type == 'condition':
                    _check_condition(node)

    def _check_substitution(node, current_section):
        raw = _text(node)
        m = _SUB_SHAPE.match(raw)
        if not m:
            if _SUB_ANY.match(raw) and ':' not in raw:
                add('ERROR', node,
                    f'malformed substitution {raw}: expected '
                    '${section:option} or ${:option}')
            elif _SUB_ANY.match(raw):
                add('ERROR', node,
                    f'malformed substitution {raw}: identifiers may only '
                    'contain letters, digits, dash, dot, underscore, space')
            else:
                add('ERROR', node,
                    f'malformed substitution {raw}: expected '
                    '${section:option} or ${:option}')
            return
        sec, opt = m.groups()
        if sec == '__environ__':
            return  # environment variables: any name is plausible
        if sec == '':
            if opt not in sections.get(current_section, set()) \
                    and opt != '_buildout_section_name_':
                add('WARNING', node,
                    f'${{:{opt}}} has no matching option in [{current_section}]')
        else:
            # options the buildout provides implicitly, whether or not the
            # file sets them (zc.buildout.buildout._initialize)
            implicit = {'directory', 'installed'} if sec == 'buildout' else set()
            if sec not in sections:
                add('WARNING', node,
                    f'substitution references unknown section [{sec}]')
            elif opt not in sections[sec] and opt not in implicit:
                add('WARNING', node,
                    f'substitution references unknown option {sec}:{opt}')

    def _check_condition(node):
        expr = _text(node)
        # token spans ': expr ]' — strip both ends
        expr = expr[1:].rstrip()
        if expr.endswith(']'):
            expr = expr[:-1]
        expr = expr.replace('\\x23', '#').replace('\\x3b', ';')
        try:
            from packaging.markers import Marker
            Marker(expr)
            return
        except Exception:
            pass
        import ast
        try:
            ast.parse(expr, mode='eval')
        except SyntaxError:
            add('WARNING', node,
                'conditional expression is neither a PEP 508 marker nor '
                f'valid Python: {expr[:60]}')

    def _iter(node):
        yield node
        for child in node.children:
            yield from _iter(child)

    check_references()
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(prog='buildout-lint',
                                 description=__doc__.splitlines()[0])
    ap.add_argument('files', nargs='+', help='configuration files to lint')
    args = ap.parse_args(argv)

    parser = make_parser()

    findings = []
    for path in args.files:
        if not Path(path).is_file():
            findings.append(Finding('ERROR', path, 0, 0, 'file not found'))
            continue
        findings.extend(lint_file(path, parser))
    for finding in findings:
        print(finding)
    return 1 if any(f.level == 'ERROR' for f in findings) else 0


if __name__ == '__main__':
    sys.exit(main())
