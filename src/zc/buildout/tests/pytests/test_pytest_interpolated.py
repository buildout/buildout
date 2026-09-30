"""Tests for the --interpolated flag of the query and annotate commands.

Raw output (as written in the configuration files) stays the default;
--interpolated shows the values with ${...} substitutions applied, the
way recipes see them.
"""
from zc.buildout.tests.pytests.conftest import (
    NORMALIZERS_BUILDOUT,
    assert_output,
)

N = NORMALIZERS_BUILDOUT

CONFIG = '''
[buildout]
parts =

[greeting]
message = hello ${greeting:audience}
audience = world
signature =
  yours
  ${greeting:audience}
'''


def test_query_raw_is_default(buildout_env):
    buildout = buildout_env['buildout']
    system = buildout_env['system']
    write = buildout_env['write']

    write('buildout.cfg', CONFIG)

    # Without the flag, query prints the raw, uninterpolated value.
    assert_output(
        system([buildout, 'query', 'greeting:message']),
        'hello ${greeting:audience}',
        N,
    )
    assert_output(
        system([buildout, 'query', 'greeting:audience']),
        'world',
        N,
    )


def test_query_interpolated(buildout_env):
    buildout = buildout_env['buildout']
    system = buildout_env['system']
    write = buildout_env['write']

    write('buildout.cfg', CONFIG)

    # With the flag, the value is shown as recipes see it.
    assert_output(
        system([buildout, 'query', 'greeting:message', '--interpolated']),
        'hello world',
        N,
    )
    # The flag may also be given before the section:key argument.
    assert_output(
        system([buildout, 'query', '--interpolated', 'greeting:message']),
        'hello world',
        N,
    )
    # Multi-line values are interpolated too.
    assert_output(
        system([buildout, 'query', 'greeting:signature', '--interpolated']),
        '''
yours
world
''',
        N,
    )
    # Combined with -v, the section and key are still displayed first.
    assert_output(
        system([buildout, '-v', 'query', 'greeting:message', '--interpolated']),
        '''
${greeting:message}
hello world
''',
        N,
    )


def test_query_interpolated_with_command_line_assignment(buildout_env):
    buildout = buildout_env['buildout']
    system = buildout_env['system']
    write = buildout_env['write']

    write('buildout.cfg', CONFIG)

    # Assignments are part of the cooked configuration recipes see.
    assert_output(
        system([buildout, 'greeting:audience=mars',
                'query', 'greeting:message', '--interpolated']),
        'hello mars',
        N,
    )
    # The raw view still shows the template.
    assert_output(
        system([buildout, 'greeting:audience=mars',
                'query', 'greeting:message']),
        'hello ${greeting:audience}',
        N,
    )


def test_query_interpolated_errors(buildout_env):
    buildout = buildout_env['buildout']
    system = buildout_env['system']
    write = buildout_env['write']

    write('buildout.cfg', CONFIG)

    assert_output(
        system([buildout, 'query', '--interpolated']),
        'Error: The query command requires a single argument.',
        N,
    )
    assert_output(
        system([buildout, 'query', 'greeting:nope', '--interpolated']),
        'Error: Key not found: nope',
        N,
    )
    assert_output(
        system([buildout, 'query', 'nope:message', '--interpolated']),
        'Error: Section not found: nope',
        N,
    )


def test_annotate_raw_is_default(buildout_env):
    buildout = buildout_env['buildout']
    system = buildout_env['system']
    write = buildout_env['write']

    write('buildout.cfg', CONFIG)

    # Without the flag, annotate shows the raw values.
    assert_output(
        system([buildout, 'annotate', 'greeting']),
        '''
Annotated sections
==================

[greeting]
audience= world
    buildout.cfg
message= hello ${greeting:audience}
    buildout.cfg
signature= yours
${greeting:audience}
    buildout.cfg
''',
        N,
    )


def test_annotate_interpolated(buildout_env):
    buildout = buildout_env['buildout']
    system = buildout_env['system']
    write = buildout_env['write']

    write('buildout.cfg', CONFIG)

    # With the flag, values are shown as recipes see them, while the
    # origin of each value is still reported.
    assert_output(
        system([buildout, 'annotate', '--interpolated', 'greeting']),
        '''
Annotated sections
==================

[greeting]
audience= world
    buildout.cfg
message= hello world
    buildout.cfg
signature= yours
world
    buildout.cfg
''',
        N,
    )

    # The flag also works without an explicit section; the interpolated
    # greeting section is part of the full output.
    assert_output(
        system([buildout, 'annotate', '--interpolated']),
        '''
...
[greeting]
audience= world
    buildout.cfg
message= hello world
    buildout.cfg
...
''',
        N,
    )


VALUES_CONFIG = """
[buildout]
parts =

[base]
letters = a

[values]
<= base
letters += b
letters -= a
"""


def test_annotate_verbose_shows_removal_history(buildout_env):
    """Verbose annotate keeps the -= entry's history block.

    Mutation round 2026-09-30: dropping the REMOVE HistoryItem survived
    both suites. The directive line survives regardless (it is value
    text); the kill lives in the sub-block layer beneath it.
    """
    buildout = buildout_env['buildout']
    system = buildout_env['system']
    write = buildout_env['write']

    write('buildout.cfg', VALUES_CONFIG)
    out = system([buildout, '-v', 'annotate', 'values'])
    # Windows text-mode stdout renders \n as \r\n; the assertions pin
    # the logical lines, not the platform line ending.
    out = out.replace('\r\n', '\n')

    assert 'letters -= a\n\n   IN buildout.cfg' in out
    assert 'letters += b\n\n   IN buildout.cfg' in out


def test_annotate_verbose_history_order(buildout_env):
    """Multi-item histories print oldest operation last.

    The ``bin-directory`` option carries AS DEFAULT_VALUE and SET VALUE
    items; a history-reversal mutant flips their print order.
    """
    buildout = buildout_env['buildout']
    system = buildout_env['system']
    write = buildout_env['write']

    write('buildout.cfg', VALUES_CONFIG)
    out = system([buildout, '-v', 'annotate', 'buildout'])

    block = out[out.index('bin-directory='):]
    block = block[:block.index('develop-eggs-directory')]
    assert 'AS DEFAULT_VALUE' in block
    assert block.index('AS DEFAULT_VALUE') < block.index('SET VALUE')
