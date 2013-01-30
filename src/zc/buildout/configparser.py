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
import logging

logger = logging.getLogger('zc.buildout')

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
    r'\[\s*'                     # opening bracket '[' then optional spaces
    r'(?P<header>[^\s[\]:{}]+)'  # header named group to capture the section name
    r'\s*:?\s*'                  # optional ':' separator between name and expression with possible spaces
    r'(?P<expression>.*)'        # optional expression named group to capture an arbitrary Python expression
    r'\s*]'                      # optional spaces then closing bracket '[' 
    r'\s*([#;].*)?$'             # optional comments at end of line, marked by '#' or ';', ignored
    ).match

option_start = re.compile(
    r'(?P<name>[^\s{}[\]=:]+\s*[-+]?)'
    r'='
    r'(?P<value>.*)$').match
leading_blank_lines = re.compile(r"^(\s*\n)+")

def parse(fp, fpname, exp_globals=None):
    """Parse a sectioned setup file.

    The sections in setup file contains a title line at the top,
    indicated by a name in square brackets (`[]'), plus key/value
    options lines, indicated by `name: value' format lines.
    Continuations are represented by an embedded newline then
    leading whitespace.  Blank lines, lines beginning with a '#',
    and just about everything else are ignored.

    The title line is in the form [title:expression] where expression is an
    arbitrary Python expression. Sections with an expression that evaluates to 
    False are ignored.

    exp_globals is a callable returning a mapping of defaults used as globals 
    during the evaluation of a section conditional expression.
    """
    sections = {}
    # the current section condition, possibly updated from a section expression
    section_condition = True                  
    context = None
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
            if not section_condition:
                #skip section based on its expression condition
                continue
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
                # reset to True when starting a new section
                section_condition = True 

                # section header
                sectname = mo.group('header')

                # filter out sections with an expression that eval to false
                exp = mo.group('expression').strip()
                if exp:
                    # lazily cache actual expression globals as needed
                    if not context:
                        context = exp_globals() if exp_globals else {}
                    # ignore section with an expression that eval to false
                    section_condition = eval(exp, context)
                    if not section_condition:
                        logger.debug('Ignoring section with conditional expression: [%(sectname)s:%(exp)s]' % locals())
                        continue

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
                    if not section_condition:
                        # filter out options of conditionally ignored section
                        continue
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
