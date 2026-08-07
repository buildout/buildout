"""Text handling helpers needed by the vendored ``pkg_resources``.

This file contains the functions ``yield_lines``, ``drop_comment`` and
``join_continuation`` (plus their helpers) copied unchanged from
``jaraco.text`` 4.0.0, as vendored by setuptools v81.0.0 in
``setuptools/_vendor/jaraco/text/__init__.py``.

jaraco.text has the following license statement.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to
deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
IN THE SOFTWARE.

"""

import functools
import itertools
from collections.abc import Iterable


def _nonblank(str):
    return str and not str.startswith('#')


@functools.singledispatch
def yield_lines(iterable):
    r"""
    Yield valid lines of a string or iterable.

    >>> list(yield_lines(''))
    []
    >>> list(yield_lines(['foo', 'bar']))
    ['foo', 'bar']
    >>> list(yield_lines('foo\nbar'))
    ['foo', 'bar']
    >>> list(yield_lines('\nfoo\n#bar\nbaz #comment'))
    ['foo', 'baz #comment']
    >>> list(yield_lines(['foo\nbar', 'baz', 'bing\n\n\n']))
    ['foo', 'bar', 'baz', 'bing']
    """
    return itertools.chain.from_iterable(map(yield_lines, iterable))


@yield_lines.register(str)
def _(text):
    return clean(text.splitlines())


def clean(lines: Iterable[str]):
    """
    Yield non-blank, non-comment elements from lines.
    """
    return filter(_nonblank, map(str.strip, lines))


def drop_comment(line):
    """
    Drop comments.

    >>> drop_comment('foo # bar')
    'foo'

    A hash without a space may be in a URL.

    >>> drop_comment('http://example.com/foo#bar')
    'http://example.com/foo#bar'
    """
    return line.partition(' #')[0]


def join_continuation(lines):
    r"""
    Join lines continued by a trailing backslash.

    >>> list(join_continuation(['foo \\', 'bar', 'baz']))
    ['foobar', 'baz']
    >>> list(join_continuation(['foo \\', 'bar', 'baz']))
    ['foobar', 'baz']
    >>> list(join_continuation(['foo \\', 'bar \\', 'baz']))
    ['foobarbaz']

    Not sure why, but...
    The character preceding the backslash is also elided.

    >>> list(join_continuation(['goo\\', 'dly']))
    ['godly']

    A terrible idea, but...
    If no line is available to continue, suppress the lines.

    >>> list(join_continuation(['foo', 'bar\\', 'baz\\']))
    ['foo']
    """
    lines = iter(lines)
    for item in lines:
        while item.endswith('\\'):
            try:
                item = item[:-2].strip() + next(lines)
            except StopIteration:
                return
        yield item
