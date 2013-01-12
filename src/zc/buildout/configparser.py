##############################################################################
#
# Copyright Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

# The following copied from Python 2 config parser because:
# - The py3 configparser isn't backward compatible
# - Both strip option values in undesireable ways
# - dict of dicts is a much simpler api

import re
import textwrap

class Error(Exception):
    """Base class for ConfigParser exceptions."""

    def _get_message(self):
        """Getter for 'message'; needed only to override deprecation in
        BaseException."""
        return self.__message

    def _set_message(self, value):
        """Setter for 'message'; needed only to override deprecation in
        BaseException."""
        self.__message = value

    # BaseException.message has been deprecated since Python 2.6.  To prevent
    # DeprecationWarning from popping up over this pre-existing attribute, use
    # a new property that takes lookup precedence.
    message = property(_get_message, _set_message)

    def __init__(self, msg=''):
        self.message = msg
        Exception.__init__(self, msg)

    def __repr__(self):
        return self.message

    __str__ = __repr__

class ParsingError(Error):
    """Raised when a configuration file does not follow legal syntax."""

    def __init__(self, filename):
        Error.__init__(self, 'File contains parsing errors: %s' % filename)
        self.filename = filename
        self.errors = []

    def append(self, lineno, line):
        self.errors.append((lineno, line))
        self.message += '\n\t[line %2d]: %s' % (lineno, line)

class MissingSectionHeaderError(ParsingError):
    """Raised when a key-value pair is found before any section header."""

    def __init__(self, filename, lineno, line):
        Error.__init__(
            self,
            'File contains no section headers.\nfile: %s, line: %d\n%r' %
            (filename, lineno, line))
        self.filename = filename
        self.lineno = lineno
        self.line = line

section_header = re.compile(
    r'\[\s*(?P<header>[^\s[\]:{}]+)\s*]\s*([#;].*)?$').match
option_start = re.compile(
    r'(?P<name>[^\s{}[\]=:]+\s*[-+]?)'
    r'='
    r'(?P<value>.*)$').match
leading_blank_lines = re.compile(r"^(\s*\n)+")

def parse(fp, fpname):
    """Parse a sectioned setup file.

    The sections in setup file contains a title line at the top,
    indicated by a name in square brackets (`[]'), plus key/value
    options lines, indicated by `name: value' format lines.
    Continuations are represented by an embedded newline then
    leading whitespace.  Blank lines, lines beginning with a '#',
    and just about everything else are ignored.
    """
    sections = {}
    cursect = None                            # None, or a dictionary
    blockmode = None
    optname = None
    lineno = 0
    e = None                                  # None, or an exception
    while True:
        line = fp.readline()
        if not line:
            break # EOF

        lineno = lineno + 1

        if line[0] in '#;':
            continue # comment

        if line[0].isspace() and cursect is not None and optname:
            # continuation line
            if blockmode:
                line = line.rstrip()
            else:
                line = line.strip()
                if not line:
                    continue
            cursect[optname] = "%s\n%s" % (cursect[optname], line)
        else:
            mo = section_header(line)
            if mo:
                # section header
                sectname = mo.group('header')
                if sectname in sections:
                    cursect = sections[sectname]
                else:
                    sections[sectname] = cursect = {}
                # So sections can't start with a continuation line
                optname = None
            elif cursect is None:
                if not line.strip():
                    continue
                # no section header in the file?
                raise MissingSectionHeaderError(fpname, lineno, line)
            else:
                mo = option_start(line)
                if mo:
                    # option start line
                    optname, optval = mo.group('name', 'value')
                    optname = optname.rstrip()
                    optval = optval.strip()
                    cursect[optname] = optval
                    blockmode = not optval
                elif not (optname or line.strip()):
                    # blank line after section start
                    continue
                else:
                    # a non-fatal parsing error occurred.  set up the
                    # exception but keep going. the exception will be
                    # raised at the end of the file and will contain a
                    # list of all bogus lines
                    if not e:
                        e = ParsingError(fpname)
                    e.append(lineno, repr(line))

    # if any parsing errors occurred, raise an exception
    if e:
        raise e

    for sectname in sections:
        section = sections[sectname]
        for name in section:
            value = section[name]
            if value[:1].isspace():
                section[name] = leading_blank_lines.sub(
                    '', textwrap.dedent(value.rstrip()))

    return sections
