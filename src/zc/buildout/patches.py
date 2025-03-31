##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
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

def patch_Distribution():
    try:
        from pkg_resources import Distribution
        from .compat import version
    except ImportError:
        return

    def hashcmp(self):
        if hasattr(self, '_hashcmp'):
            return self._hashcmp
        else:
            try:
                parsed_version = self.parsed_version
            except Exception:
                # You get here when there is an distribution on PyPI
                # with a version that is no longer seen as valid.
                # I want to catch version.InvalidVersion, but it may
                # come from a different place then I think.
                parsed_version = version.Version("0.0.0")
            self._hashcmp = result = (
                parsed_version,
                self.precedence,
                self.key,
                self.location,
                self.py_version or '',
                self.platform or '',
            )
            return result

    setattr(Distribution, 'hashcmp', property(hashcmp))


patch_Distribution()


def patch_PackageIndex():
    """Patch the package index from setuptools.

    Main goal: check the package urls on an index page to see if they are
    compatible with the Python version.
    """

    try:
        import logging
        logging.getLogger('pip._internal.index.collector').setLevel(logging.ERROR)
        from setuptools.package_index import PackageIndex
        from setuptools.package_index import URL_SCHEME
        from setuptools.package_index import distros_for_url

        try:
            # pip 22.2+
            from pip._internal.index.collector import IndexContent
        except ImportError:
            # pip 22.1-
            from pip._internal.index.collector import HTMLPage as IndexContent

        from pip._internal.index.collector import parse_links
        from pip._internal.index.package_finder import _check_link_requires_python
        from pip._internal.models.target_python import TargetPython
        from urllib.error import HTTPError
    except ImportError:
        import logging
        logger = logging.getLogger('zc.buildout.patches')
        logger.warning(
            'Requires-Python support missing and could not be patched into '
            'zc.buildout. \n\n',
            exc_info=True
        )
        return

    PY_VERSION_INFO = TargetPython().py_version_info

    # method copied over from setuptools 46.1.3
    # Unchanged in setuptools 70.0.0.
    def process_url(self, url, retrieve=False):
        """Evaluate a URL as a possible download, and maybe retrieve it"""
        if url in self.scanned_urls and not retrieve:
            return
        self.scanned_urls[url] = True
        if not URL_SCHEME(url):
            self.process_filename(url)
            return
        else:
            dists = list(distros_for_url(url))
            if dists:
                if not self.url_ok(url):
                    return
                self.debug("Found link: %s", url)

        if dists or not retrieve or url in self.fetched_urls:
            list(map(self.add, dists))
            return  # don't need the actual page

        if not self.url_ok(url):
            self.fetched_urls[url] = True
            return

        self.info("Reading %s", url)
        self.fetched_urls[url] = True  # prevent multiple fetch attempts
        tmpl = "Download error on %s: %%s -- Some packages may not be found!"
        f = self.open_url(url, tmpl % url)
        if f is None:
            return
        if isinstance(f, HTTPError) and f.code == 401:
            self.info("Authentication error: %s" % f.msg)
        self.fetched_urls[f.url] = True
        if 'html' not in f.headers.get('content-type', '').lower():
            f.close()  # not html, we can't process it
            return

        base = f.url  # handle redirects
        page = f.read()

        # --- LOCAL CHANGES MADE HERE: ---

        if isinstance(page, str):
            page = page.encode('utf8')
            charset = 'utf8'
        else:
            if isinstance(f, HTTPError):
                # Errors have no charset, assume latin1:
                charset = 'latin-1'
            else:
                try:
                    charset = f.headers.get_param('charset') or 'latin-1'
                except AttributeError:
                    # Python 2
                    charset = f.headers.getparam('charset') or 'latin-1'

        try:
            content_type = f.getheader('content-type')
        except AttributeError:
            # On at least Python 2.7:
            # addinfourl instance has no attribute 'getheader'
            content_type = "text/html"

        try:
            # pip 22.2+
            html_page = IndexContent(
                page,
                content_type=content_type,
                encoding=charset,
                url=base,
                cache_link_parsing=False,
            )
        except TypeError:
            try:
                # pip 20.1-22.1
                html_page = IndexContent(page, charset, base, cache_link_parsing=False)
            except TypeError:
                # pip 20.0 or older
                html_page = IndexContent(page, charset, base)

        # https://github.com/buildout/buildout/issues/598
        # use_deprecated_html5lib is a required addition in pip 22.0/22.1
        # and it is gone already in 22.2
        try:
            plinks = parse_links(html_page, use_deprecated_html5lib=False)
        except TypeError:
            plinks = parse_links(html_page)
        plinks = list(plinks)

        # --- END OF LOCAL CHANGES ---

        if not isinstance(page, str):
            # In Python 3 and got bytes but want str.
            page = page.decode(charset, "ignore")
        f.close()

        # --- LOCAL CHANGES MADE HERE: ---

        for link in plinks:
            if _check_link_requires_python(link, PY_VERSION_INFO):
                self.process_url(link.url)

        # --- END OF LOCAL CHANGES ---

        if url.startswith(self.index_url) and getattr(f, 'code', None) != 404:
            page = self.process_index(url, page)

    setattr(PackageIndex, 'process_url', process_url)


patch_PackageIndex()


def patch_interpret_distro_name():
    """Goal: recognize distro names better.

    interpret_distro_name was changed as part of
    https://github.com/pypa/setuptools/pull/2822
    This landed in setuptools 70.

    We seem to need this version, to avoid problems recognizing distro names.
    'basename' is for example 'mauritstest.namespacepackage-1.0.0'
    The new code correctly handles this as project name
    ''mauritstest.namespacepackage', instead of yielding multiple distros.
    """
    try:
        from packaging import version
        from pkg_resources import Distribution
        from pkg_resources import SOURCE_DIST
        from setuptools import package_index

        import re
        import setuptools
    except ImportError:
        return

    if version.parse(setuptools.__version__) >= version.Version("70"):
        # Patch is not needed.
        return

    def interpret_distro_name(
        location, basename, metadata, py_version=None, precedence=SOURCE_DIST, platform=None
    ):
        """Generate the interpretation of a source distro name

        Note: if `location` is a filesystem filename, you should call
        ``pkg_resources.normalize_path()`` on it before passing it to this
        routine!
        """

        parts = basename.split('-')
        if not py_version and any(re.match(r'py\d\.\d$', p) for p in parts[2:]):
            # it is a bdist_dumb, not an sdist -- bail out
            return

        # find the pivot (p) that splits the name from the version.
        # infer the version as the first item that has a digit.
        for p in range(len(parts)):
            if parts[p][:1].isdigit():
                break
        else:
            p = len(parts)

        yield Distribution(
            location,
            metadata,
            '-'.join(parts[:p]),
            '-'.join(parts[p:]),
            py_version=py_version,
            precedence=precedence,
            platform=platform,
        )

    package_index.interpret_distro_name = interpret_distro_name


patch_interpret_distro_name()


def patch_pkg_resources_requirement_contains():
    """Patch pkg_resources.Requirement contains method.

    What this hopefully solves, is checking if a Requirement contains
    a Distribution, without the key needing to be exactly the same.
    We want to compare normalized names.
    """
    try:
        from pkg_resources import Distribution
        from pkg_resources import Requirement
        from zc.buildout.utils import normalize_name
    except ImportError:
        return

    def __contains__(self, item):
        if isinstance(item, Distribution):
            # if item.key != self.key:
            if normalize_name(item.key) != normalize_name(self.key):
                return False

            item = item.version

        # Allow prereleases always in order to match the previous behavior of
        # this method. In the future this should be smarter and follow PEP 440
        # more accurately.
        try:
            return self.specifier.contains(item, prereleases=True)
        except Exception:
            # For example on https://pypi.org/simple/zope-exceptions/
            # the first distribution is zope.exceptions-3.4dev-r73107.tar.gz
            # I want to catch version.InvalidVersion, but it may
            # come from a different place then I think.
            return False

    Requirement.__contains__ = __contains__


patch_pkg_resources_requirement_contains()


def patch_pkg_resources_working_set_find():
    """Patch pkg_resources.WorkingSet find method.

    setuptools 75.8.1 fixed wheel file naming to follow the binary distribution
    specification.  This broke a lot for us, especially when using editable
    installs.  We fixed several parts of our code.

    setuptools 75.8.2 fixed some of the breakage by updating the `find` method
    of working sets.  When finding a requirement, it now considers several
    candidates: different spellings of the requirement name.
    See https://github.com/pypa/setuptools/pull/4856

    A lot of remaining problems in Buildout are fixed if we use this setuptools
    version.  So what we do in this patch, is to check which setuptools version
    is used, and patch the 'find' method if the version is older than 75.8.2.

    But: if the version is *much* older, the patch can be applied, but calling
    the `find` method will raise:

    AttributeError: 'WorkingSet' object has no attribute 'normalized_to_canonical_keys'

    The first setuptools version that has this, is 61.0.0.
    So don't patch versions that are older than that.

    Alternatively, we could drop support.  That is fine with me.
    """
    try:
        from importlib.metadata import version
        from packaging.version import parse
        from packaging.version import Version

        setuptools_version = parse(version("setuptools"))
        if setuptools_version >= Version("75.8.2"):
            return
        if setuptools_version < Version("61"):
            return
    except Exception:
        return

    try:
        from pkg_resources import Distribution
        from pkg_resources import Requirement
        from pkg_resources import safe_name
        from pkg_resources import VersionConflict
        from pkg_resources import WorkingSet
    except ImportError:
        return

    def find(self, req):
        """Find a distribution matching requirement `req`

        Note: I removed the type hints, because they failed on Python 3.9:

          TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'

        If there is an active distribution for the requested project, this
        returns it as long as it meets the version requirement specified by
        `req`.  But, if there is an active distribution for the project and it
        does *not* meet the `req` requirement, ``VersionConflict`` is raised.
        If there is no active distribution for the requested project, ``None``
        is returned.
        """
        dist = None

        candidates = (
            req.key,
            self.normalized_to_canonical_keys.get(req.key),
            safe_name(req.key).replace(".", "-"),
        )

        for candidate in filter(None, candidates):
            dist = self.by_key.get(candidate)
            if dist:
                req.key = candidate
                break

        if dist is not None and dist not in req:
            # XXX add more info
            raise VersionConflict(dist, req)
        return dist

    WorkingSet.find = find


patch_pkg_resources_working_set_find()


def patch_find_packages():
    """
    Patch setuptools.package_index.PackageIndex find_packages method.
    Implements PEP 503
    """
    try:
        from setuptools.package_index import PackageIndex
        import re
    except ImportError:
        return

    # method copied over from setuptools 46.1.3
    # Unchanged in setuptools 77.0.1.
    def find_packages(self, requirement):
        url_name = re.sub(r"[-_.]+", "-", requirement.unsafe_name).lower()
        self.scan_url(self.index_url + url_name + '/')

        if not self.package_pages.get(requirement.key):
            # Fall back to safe version of the name
            self.scan_url(self.index_url + requirement.project_name + '/')

        if not self.package_pages.get(requirement.key):
            # We couldn't find the target package, so search the index page too
            self.not_found_in_index(requirement)

        for url in list(self.package_pages.get(requirement.key, ())):
            # scan each page that might be related to the desired package
            self.scan_url(url)

    setattr(PackageIndex, 'find_packages', find_packages)


patch_find_packages()
