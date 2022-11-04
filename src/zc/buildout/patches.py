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

        def hashcmp(self):
            if hasattr(self, '_hashcmp'):
                return self._hashcmp
            else:
                self._hashcmp = result = (
                    self.parsed_version,
                    self.precedence,
                    self.key,
                    self.location,
                    self.py_version or '',
                    self.platform or '',
                )
                return result

        setattr(Distribution, 'hashcmp', property(hashcmp))
    except ImportError:
        return


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
        from pip._vendor import six
        from pip._vendor.six.moves import urllib

        PY_VERSION_INFO = TargetPython().py_version_info

        # method copied over from setuptools 46.1.3
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
            if isinstance(f, urllib.error.HTTPError) and f.code == 401:
                self.info("Authentication error: %s" % f.msg)
            self.fetched_urls[f.url] = True
            if 'html' not in f.headers.get('content-type', '').lower():
                f.close()  # not html, we can't process it
                return

            base = f.url  # handle redirects
            page = f.read()

            # --- LOCAL CHANGES MADE HERE: ---

            if isinstance(page, six.text_type):
                page = page.encode('utf8')
                charset = 'utf8'
            else:
                if isinstance(f, urllib.error.HTTPError):
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

    except ImportError:
        import logging
        logger = logging.getLogger('zc.buildout.patches')
        logger.warning(
            'Requires-Python support missing and could not be patched into '
            'zc.buildout. \n\n',
            exc_info=True
        )
        return


patch_PackageIndex()
