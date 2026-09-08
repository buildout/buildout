# tree-sitter-buildout

Tree-sitter grammar for zc.buildout configuration files (`buildout.cfg` and
friends), plus a linter built on top of it.

Status: working. The grammar parses sections, conditional section headers,
options (`=`, `+=`, `-=`), multiline values with continuations,
`${section:option}` substitutions, `<=` macro options and `=>` dependency
annotations (including their indented continuations). See `grammar.js` for
the exact scope and the deliberate deviations from
`src/zc/buildout/configparser.py` (the hand-rolled reference parser this
mirrors).

## Layout

- `grammar.js` — the grammar definition (the source of truth)
- `src/` — generated parser (`tree-sitter generate --abi=14`), committed so
  consumers do not need the CLI
- `test/corpus/` — tree-sitter corpus tests (`tree-sitter test`)
- `linter/` — unittest suite (stdlib, no pytest) and lint corpus for the
  *packaged* linter
  (`zc.buildout.lint`, see below); `corpus/clean` files must lint without
  any finding, `corpus/warnings` must produce WARNINGs but no ERROR,
  `corpus/errors` must produce an ERROR

## The packaged linter: buildout-lint

The linter itself lives in the zc.buildout package as `zc.buildout.lint`
and is installed as a console script:

```sh
pip install zc.buildout[linter]
buildout-lint buildout.cfg [...]
```

The generated parser is vendored into the wheel under
`zc/buildout/grammar/` (C source only) and compiled on first use with the
system C compiler — override with the `CC` environment variable — into a
cache in the temp dir. Neither the tree-sitter CLI nor node is needed at
lint time. The `linter` extra pins `tree-sitter>=0.23.2,<0.27`; the grammar
is generated at ABI 14 so every py-tree-sitter in that range works,
including 0.23.2 (the last release with Python 3.9 wheels).

Exit status is 1 if any ERROR-level finding, 0 otherwise. See the module
docstring for the exact checks; resolution is file-local, so reference
checks are WARNING-level to tolerate options injected by recipes, macros
and `extends` layering.

## Development

```sh
make grammar-test   # regenerate parser.c (ABI 14) + run tree-sitter corpus
make sync-grammar   # copy the generated parser into src/zc/buildout/grammar/
make lint           # lint repo configs + run linter/corpus tests
                    # (bootstraps venvs/linter with -e '.[linter]')
```

`make sync-grammar` after every parser regeneration — CI fails
(`.github/workflows/lint.yml`) when the vendored copy drifts from
`tree-sitter-buildout/src/`.

Tests: `python -m unittest discover -s tree-sitter-buildout/linter`
(skips if py-tree-sitter is not installed).

## Gotchas discovered while writing this

- **tree-sitter's default `extras` is `[/\s/]`** — whitespace *and newlines*
  are skipped implicitly between tokens. For this line-oriented format that
  silently merged values with their continuation lines. This grammar sets
  `extras: []` explicitly; do not reintroduce a whitespace extra.
- Tokens that can match the empty string (`/[ \t]*/` as a standalone rule
  member) break parsing without a generate-time error — use
  `optional(/[ \t]+/)` instead.
- Rust regex syntax (what tree-sitter compiles to) requires escaping `[`
  inside character classes: `[^\s{}\[\]=:]+`, unlike JS regex literals.
- Trailing trivia (comments/blank lines) after an option or annotation is
  genuinely ambiguous (attach to the open statement or to the enclosing
  section?); resolved via GLR `conflicts` entries for `section`, `option`
  and `dependency_annotation`.
