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

SECTCRE = re.compile(
    r'\['                                 # [
    r'(?P<header>[^]]+)'                  # very permissive!
    r'\]'                                 # ]
    )
OPTCRE = re.compile(
    r'(?P<option>[^:=\s][^:=]*)'          # very permissive!
    r'\s*(?P<vi>[:=])\s*'                 # any number of space/tab,
                                          # followed by separator
                                          # (either : or =), followed
                                          # by any # space/tab
    r'(?P<value>.*)$'                     # everything up to eol
    )

def parse(fp, fpname):
    """Parse a sectioned setup file.

    The sections in setup file contains a title line at the top,
    indicated by a name in square brackets (`[]'), plus key/value
    options lines, indicated by `name: value' format lines.
    Continuations are represented by an embedded newline then
    leading whitespace.  Blank lines, lines beginning with a '#',
    and just about everything else are ignored.
    """
    _sections = {}
    cursect = None                            # None, or a dictionary
    optname = None
    lineno = 0
    e = None                                  # None, or an exception
    while True:
        line = fp.readline()
        if not line:
            break
        lineno = lineno + 1
        # comment or blank line?
        if line.strip() == '' or line[0] in '#;':
            continue
        if line.split(None, 1)[0].lower() == 'rem' and line[0] in "rR":
            # no leading whitespace
            continue
        # continuation line?
        if line[0].isspace() and cursect is not None and optname:
            value = line.strip()
            if value:
                cursect[optname] = "%s\n%s" % (cursect[optname], value)
        # a section header or option header?
        else:
            # is it a section header?
            mo = SECTCRE.match(line)
            if mo:
                sectname = mo.group('header')
                if sectname in _sections:
                    cursect = _sections[sectname]
                else:
                    cursect = {}
                    _sections[sectname] = cursect
                # So sections can't start with a continuation line
                optname = None
            # no section header in the file?
            elif cursect is None:
                raise MissingSectionHeaderError(fpname, lineno, line)
            # an option line?
            else:
                mo = OPTCRE.match(line)
                if mo:
                    optname, vi, optval = mo.group('option', 'vi', 'value')
                    # This check is fine because the OPTCRE cannot
                    # match if it would set optval to None
                    if optval is not None:
                        if vi in ('=', ':') and ';' in optval:
                            # ';' is a comment delimiter only if it follows
                            # a spacing character
                            pos = optval.find(';')
                            if pos != -1 and optval[pos-1].isspace():
                                optval = optval[:pos]
                        optval = optval.strip()
                    # allow empty values
                    if optval == '""':
                        optval = ''
                    optname = optname.rstrip()
                    cursect[optname] = optval
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

    return _sections
