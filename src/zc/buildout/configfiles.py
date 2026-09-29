##############################################################################
#
# Copyright (c) 2005-2009 Zope Foundation and Contributors.
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
"""Configuration file opening, parsing, and extends handling.

Everything here moved out of ``zc.buildout.buildout`` unchanged; that
module re-exports these names so existing import paths keep working.
``_parse_config_file`` imports ``_default_globals`` lazily at call time
because ``zc.buildout.buildout`` owns it and imports this module.
"""

from __future__ import annotations

import copy
import os
import re
from io import StringIO, TextIOWrapper

import zc.buildout
import zc.buildout.configparser
import zc.buildout.download
from zc.buildout.annotations import (
    AnnotatedSection,
    ConfigData,
    RawSection,
    SectionKey,
    _annotate,
    _unannotate_section,
)
from zc.buildout.utils import bool_option

_isurl = re.compile('([a-zA-Z0-9+.-]+)://').match

variable_template_split = re.compile('([$]{[^}]*})').split

def _update_section(in1: dict[str, SectionKey], s2: dict[str, SectionKey]) -> dict[str, SectionKey]:
    s1 = copy.deepcopy(in1)
    # Base section 2 on section 1; section 1 is copied, with key-value pairs
    # in section 2 overriding those in section 1. If there are += or -=
    # operators in section 2, process these to add or subtract items (delimited
    # by newlines) from the preexisting values.
    s2 = copy.deepcopy(s2) # avoid mutating the second argument, which is unexpected
    # Sort on key, then on the addition or subtraction operator (+ comes first)
    for k, v in sorted(s2.items(), key=lambda x: (x[0].rstrip(' +'), x[0][-1])):
        if k.endswith('+'):
            key = k.rstrip(' +')
            implicit_value = SectionKey("", "IMPLICIT_VALUE")
            # Find v1 in s2 first; it may have been defined locally too.
            section_key = s2.get(key, s1.get(key, implicit_value))
            section_key = copy.deepcopy(section_key)
            section_key.addToValue(v.value, v.source)
            s2[key] = section_key
            del s2[k]
        elif k.endswith('-'):
            key = k.rstrip(' -')
            implicit_value = SectionKey("", "IMPLICIT_VALUE")
            # Find v1 in s2 first; it may have been set by a += operation first
            section_key = s2.get(key, s1.get(key, implicit_value))
            section_key = copy.deepcopy(section_key)
            section_key.removeFromValue(v.value, v.source)
            s2[key] = section_key
            del s2[k]

    _update_verbose(s1, s2)
    return s1

def _update_verbose(s1: dict[str, SectionKey], s2: dict[str, SectionKey]) -> None:
    for key, v2 in s2.items():
        if key in s1:
            v1 = s1[key]
            v1.overrideValue(v2)
        else:
            s1[key] = copy.deepcopy(v2)

def _update(in1: ConfigData, d2: ConfigData) -> ConfigData:
    d1 = copy.deepcopy(in1)
    for section, options2 in d2.items():
        if section in d1:
            d1[section] = _update_section(d1[section], options2)
        elif '<' not in options2:
            # Skip sections that extend in other sections (macros), as we don't
            # have all the data (these will be processed when the section is
            # extended)
            temp = copy.deepcopy(d2[section])
            # 641 - Process base definitions done with += and -=
            for k, v in sorted(temp.items(), key=lambda item: item[0]):
                # Process + before -, configparser resolves conflicts
                if k[-1] == '+' and k[:-2] not in temp:
                    # Turn += without a preceding = into an assignment
                    temp[k[:-2]] = temp[k]
                    del temp[k]
                elif k[-1] == '-' and k[:-2] not in temp:
                    # Turn -= without a preceding = into an empty assignment
                    temp[k[:-2]] = temp[k]
                    temp[k[:-2]].removeFromValue(
                        temp[k[:-2]].value, "IMPLICIT_VALUE"
                        )
                    del temp[k]

            # 656 - Handle multiple option assignments/extensions/removals
            # in the same file, which can happen with conditional sections
            d1[section] = _update_section({}, temp)
        else:
            d1[section] = copy.deepcopy(d2[section])

    return d1

def _validated_extends_cache(raw_download_options: dict[str, str]) -> str | None:
    """Return the extends-cache option, rejecting variable substitutions."""
    extends_cache = raw_download_options.get('extends-cache')
    if extends_cache and variable_template_split(extends_cache)[1::2]:
        raise ValueError(
            f"extends-cache '{extends_cache}' may not contain "
            "${section:variable} to expand."
        )
    return extends_cache

def _resolve_config_location(base: str, filename: str) -> tuple[str, str, bool]:
    """Resolve a config file reference against its base.

    Return the filename to open, the base for further relative
    references, and whether the file must be downloaded first.
    """
    if _isurl(filename):
        return filename, filename[:filename.rfind('/')], True
    if _isurl(base):
        if os.path.isabs(filename):
            return filename, os.path.dirname(filename), False
        filename = base + '/' + filename
        return filename, filename[:filename.rfind('/')], True
    filename = os.path.join(base, filename)
    return filename, os.path.dirname(filename), False

def _filename_for_logging(filename: str, downloaded_filename: str | None) -> str:
    if downloaded_filename:
        return f'{filename} (downloaded as {downloaded_filename})'
    return filename

def _merge_config_data(eresults: list[ConfigData]) -> ConfigData:
    """Merge per-file config dicts into one, later files winning."""
    final_result: ConfigData = {}
    for eresult in eresults:
        final_result = _update(final_result, eresult)
    return final_result

def _open_config_file(
        base: str,
        filename: str,
        seen: list[str],
        download: zc.buildout.download.Download,
        downloaded: set[str],
        ) -> tuple[str, str, TextIOWrapper, bool, str | None]:
    """Resolve ``filename`` against ``base`` and open it, downloading
    first when it is a URL.

    Record the resolved filename in ``downloaded`` and reject recursive
    includes, removing any temporary download before raising.  Return
    ``(filename, base, fp, is_temp, downloaded_filename)``.
    """
    is_temp = False
    downloaded_filename = None
    filename, base, needs_download = _resolve_config_location(base, filename)
    if needs_download:
        downloaded_filename, is_temp = download(filename)
        fp = open(downloaded_filename)  # noqa: SIM115 - returned to caller
    else:
        fp = open(filename)  # noqa: SIM115 - returned to caller
    downloaded.add(filename)

    if filename in seen:
        if is_temp:
            fp.close()
            # downloaded_filename is always set when is_temp is true.
            assert downloaded_filename is not None
            os.remove(downloaded_filename)
        raise zc.buildout.UserError("Recursive file include", seen, filename)
    return filename, base, fp, is_temp, downloaded_filename

def _parse_config_file(
        fp: StringIO | TextIOWrapper,
        filename: str,
        downloaded_filename: str | None,
        is_temp: bool,
        ) -> dict[str, dict[str, str]]:
    """Parse the open config file ``fp``, close it, and remove any
    temporary download."""
    from zc.buildout.buildout import _default_globals
    result = zc.buildout.configparser.parse(
        fp, _filename_for_logging(filename, downloaded_filename),
        _default_globals)
    fp.close()
    if is_temp:
        # downloaded_filename is always set when is_temp is true.
        assert downloaded_filename is not None
        os.remove(downloaded_filename)
    return result

def _extends_results(
        base: str,
        extends: str | None,
        seen: list[str],
        download_options: dict[str, SectionKey],
        override: dict[str, SectionKey],
        downloaded: set[str],
        user_defaults: dict[str, dict[str, SectionKey]],
        result: ConfigData,
        ) -> tuple[list[ConfigData], ConfigData, dict[str, dict[str, SectionKey]]]:
    """Process the ``extends`` option, recursively opening each file.

    Return ``(eresults, result, user_defaults)``: the configs of the
    extended files, and — when nothing is extended — ``result`` merged
    over ``user_defaults`` (which are then consumed).
    """
    # Process extends to handle nested += and -=
    eresults: list[ConfigData] = []
    if extends:
        for fname in extends.split():
            next_extend, user_defaults = _open(
                base, fname, seen, download_options, override,
                downloaded, user_defaults)
            # A recursive _open call returns the list form.
            assert isinstance(next_extend, list)
            eresults.extend(next_extend)
    else:
        if user_defaults:
            result = _update(user_defaults, result)
            user_defaults = {}
    return eresults, result, user_defaults

def _optional_extends_results(
        base: str,
        optional_extends: SectionKey | None,
        seen: list[str],
        download_options: dict[str, SectionKey],
        override: dict[str, SectionKey],
        downloaded: set[str],
        user_defaults: dict[str, dict[str, SectionKey]],
        eresults: list[ConfigData],
        ) -> dict[str, dict[str, SectionKey]]:
    """Process the ``optional-extends`` option, recursively opening each
    existing file and skipping the missing ones with a notice.

    Extend ``eresults`` in place; return the updated ``user_defaults``.
    """
    if optional_extends:
        for fname in optional_extends.value.split():
            if not os.path.exists(fname):
                print(f"optional-extends file not found: {fname}")
                continue
            next_extend, user_defaults = _open(
                base, fname, seen, download_options, override,
                downloaded, user_defaults)
            # A recursive _open call returns the list form.
            assert isinstance(next_extend, list)
            eresults.extend(next_extend)
    return user_defaults

def _ensure_download_cache(download: zc.buildout.download.Download) -> None:
    """Create the resolved extends/download cache on first use.

    Extends are downloaded while the configuration is read, which is
    before _create_cache_dirs runs; create the cache here so setting
    the option suffices on the first online run.
    """
    cache_dir = download.download_cache
    if cache_dir and not os.path.exists(cache_dir):
        os.makedirs(cache_dir, exist_ok=True)


def _open(
        base: str, filename: str, seen: list[str], download_options: dict[str, SectionKey],
        override: dict[str, SectionKey], downloaded: set[str], user_defaults: dict[str, dict[str, SectionKey]]
        ) -> tuple[ConfigData, dict[str, dict[str, SectionKey]]] | tuple[list[ConfigData], dict[str, dict[str, SectionKey]]]:
    """Open a configuration file and return the result as a dictionary,

    Recursively open other files based on buildout options found.

    Return type: a top-level call (empty ``seen``) returns the merged
    config dict; a recursive call (for ``extends``) returns the list of
    per-file config dicts.  Callers narrow with isinstance asserts.
    """
    download_options = _update_section(download_options, override)
    raw_download_options = _unannotate_section(download_options)
    newest = bool_option(raw_download_options, 'newest', 'false')
    fallback = newest and filename not in downloaded
    extends_cache = _validated_extends_cache(raw_download_options)
    download = zc.buildout.download.Download(
        raw_download_options, cache=extends_cache,
        fallback=fallback, hash_name=True)
    _ensure_download_cache(download)
    (filename, base, fp, is_temp,
     downloaded_filename) = _open_config_file(
        base, filename, seen, download, downloaded)

    root_config_file = not seen
    seen.append(filename)

    raw_result = _parse_config_file(fp, filename, downloaded_filename, is_temp)

    # Values are plain strings for now; _annotate below mutates them into
    # SectionKey objects in place.
    raw_options: RawSection = raw_result.get('buildout', {})
    extends = raw_options.pop('extends', None)
    if 'extended-by' in raw_options:
        raise zc.buildout.UserError(
            f'No-longer supported "extended-by" option found in {filename}.')

    result = _annotate(raw_result, filename)

    # The buildout section raw_options was bound to above is the same
    # object _annotate annotated in place; rebind it under its post-state
    # type for the remaining reads (before _extends_results may merge
    # result into a new dict).
    options: AnnotatedSection = result.get('buildout', {})

    if root_config_file and 'buildout' in result:
        download_options = _update_section(
            download_options, result['buildout']
        )

    # Process extends to handle nested += and -=
    eresults, result, user_defaults = _extends_results(
        base, extends, seen, download_options, override, downloaded,
        user_defaults, result)

    optional_extends = options.pop('optional-extends', None)
    user_defaults = _optional_extends_results(
        base, optional_extends, seen, download_options, override,
        downloaded, user_defaults, eresults)

    eresults.append(result)
    seen.pop()

    if root_config_file:
        return _merge_config_data(eresults), user_defaults
    else:
        return eresults, user_defaults
