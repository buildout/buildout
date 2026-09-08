// Tree-sitter grammar for zc.buildout configuration files.
//
// Mirrors the hand-rolled parser in src/zc/buildout/configparser.py:
//   - comments are full-line only, '#' or ';' in column 0
//   - section headers: [name], [name: expression], optional trailing comment
//   - options: name = value, name += value, name -= value (the +/- may be
//     separated from the name by spaces; the source parser folds it into the
//     key, e.g. "b +")
//   - option names may contain '<' and '>', so '<= base' (macro extension)
//     is an ordinary option whose name is '<'
//   - lines starting with '=>' are rewritten by the source parser to
//     '<part-dependencies> = ...'; we tag them as dependency_annotation
//   - indented lines continue the current option's value; a '#' or ';'
//     in column 0 is a comment even inside a value
//
// Deliberate deviations from configparser.py (kept out of the grammar on
// purpose, to be handled by a linter/host pass instead):
//   - conditional-section expressions are captured as one opaque token and
//     may not contain ']' (the source regex allows them by backtracking)
//   - whitespace-only lines inside an option value are blank_line nodes,
//     not continuation nodes
//   - blank lines are consumed greedily by the innermost open option;
//     value normalization (strip vs block mode, dedent) is host work

module.exports = grammar({
  name: 'buildout',

  // CRITICAL: override tree-sitter's default extras of [/\s/]. Whitespace
  // and newlines are significant in this line-oriented format (indentation
  // starts a continuation), so nothing may be skipped implicitly.
  extras: $ => [],

  // Whether a comment or blank line after a section's last option belongs
  // to that section or to the file level is genuinely ambiguous; both
  // parses are acceptable, GLR resolves it deterministically.
  conflicts: $ => [
    [$.section],
    [$.option],
    [$.dependency_annotation],
  ],

  rules: {
    source_file: $ => repeat(choice(
      $.section,
      $.comment,
      $._blank_line,
    )),

    section: $ => seq(
      $.section_header,
      repeat(choice(
        $.option,
        $.dependency_annotation,
        $.comment,
        $._blank_line,
      )),
    ),

    section_header: $ => choice(
      // plain: [name]
      seq(
        '[',
        optional(/[ \t]+/),
        $.section_name,
        optional(/[ \t]+/),
        ']',
        optional($._trailing_comment),
        $._newline,
      ),
      // conditional: [name: expression] — the source parser's expression
      // regex ([^#;]*) is greedy and backtracks to the LAST ']' on the line,
      // so expressions may themselves contain ']'. The condition token below
      // mirrors that by maximal munch: it spans ': expr ]' including the
      // closing bracket.
      seq(
        '[',
        optional(/[ \t]+/),
        $.section_name,
        optional(/[ \t]+/),
        $.condition,
        optional($._trailing_comment),
        $._newline,
      ),
    ),

    section_name: $ => /[^\s#\[\]:;{}]+/,

    // Opaque: ': arbitrary Python or PEP 508 marker expression ]', keeping
    // the leading colon and the closing bracket. Expressions may contain
    // '[' and ']' but not '#' or ';' (write those as \x23 / \x3b).
    condition: $ => token(seq(':', /[^#;\n]*\]/)),

    // Comments and blank lines do NOT close an open option in the source
    // parser (the comment check `continue`s without touching the current
    // option), so an indented line after them still appends to the value.
    option: $ => seq(
      $.option_name,
      $.assignment,
      optional($.value),
      $._newline,
      repeat(choice($.continuation, $.comment, $._blank_line)),
    ),

    // The source parser folds a trailing '+'/'-' into the key ("b +"),
    // so `a+=1` lexes with the sign inside option_name and `a += 1` with
    // the sign inside assignment. Both shapes are preserved here.
    option_name: $ => /[^\s{}\[\]=:]+/,

    assignment: $ => /[ \t]*[-+]?[ \t]*=[ \t]*/,

    value: $ => repeat1(choice(
      $.substitution,
      $.escape,
      /[^$\n]+/,
      /\$/,
    )),

    substitution: $ => token(seq('${', /[^}\n]*/, '}')),

    // '$$' escapes a literal dollar in the source parser.
    escape: $ => token('$$'),

    // The reference parser accumulates indented continuation lines after
    // '=>' into the <part-dependencies> value, just like option values.
    dependency_annotation: $ => seq(
      token(seq('=>', /[^\n]*/)),
      $._newline,
      repeat(choice($.continuation, $.comment, $._blank_line)),
    ),

    continuation: $ => seq(
      token(/[ \t]+\S[^\n]*/),
      $._newline,
    ),

    comment: $ => token(/[#;][^\n]*/),

    // after ']': either spaced or immediately attached ('[s]; c')
    _trailing_comment: $ => choice(seq(/[ \t]+/, $.comment), $.comment),

    _blank_line: $ => token(/[ \t]*\r?\n/),

    _newline: $ => /\r?\n/,
  },
});
