##############################################################################
#
# Copyright (c) 2009 Zope Foundation and Contributors.
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
"""Buildout download infrastructure"""

from __future__ import annotations

import logging
import os
import os.path
import re
import shutil
import sys
import tempfile
from hashlib import md5
from urllib.parse import urlparse
from urllib.request import urlretrieve

import zc.buildout
from zc.buildout.easy_install import realpath


class ChecksumError(zc.buildout.UserError):
    pass

class Download:
    """Configurable download utility.

    Handles the download cache and offline mode.

    Download(options=None, cache=None, namespace=None,
             offline=False, fallback=False, hash_name=False, logger=None)

    options: mapping of buildout options (e.g. a ``buildout`` config section)
    cache: path to the download cache (excluding namespaces)
    namespace: namespace directory to use inside the cache
    offline: whether to operate in offline mode
    fallback: whether to use the cache as a fallback (try downloading first)
    hash_name: whether to use a hash of the URL as cache file name
    logger: an optional logger to receive download-related log messages

    """

    def __init__(self, options: dict[str, str] | None=None, cache: str | int | None=-1, namespace: str | None=None,
                 offline: int | bool=-1, fallback: bool=False, hash_name: bool=False, logger: logging.Logger | None=None) -> None:
        if options is None:
            options = {}
        self.directory = options.get('directory', '')
        self.cache: str | None
        if cache == -1:
            self.cache = options.get('download-cache')
        elif isinstance(cache, str):
            self.cache = cache
        else:
            self.cache = None
        self.namespace = namespace
        self.offline = offline
        if offline == -1:
            self.offline = (options.get('offline') == 'true'
                            or options.get('install-from-cache') == 'true')
        self.fallback = fallback
        self.hash_name = hash_name
        self.logger = logger or logging.getLogger('zc.buildout')

    @property
    def download_cache(self) -> str | None:
        if self.cache is not None:
            return realpath(os.path.join(self.directory, self.cache))

    @property
    def cache_dir(self) -> str | None:
        if self.download_cache is not None:
            return os.path.join(self.download_cache, self.namespace or '')

    def __call__(self, url: str, md5sum: str | None=None, path: str | None=None) -> tuple[str, bool]:
        """Download a file according to the utility's configuration.

        url: URL to download
        md5sum: MD5 checksum to match
        path: where to place the downloaded file

        Returns the path to the downloaded file.

        """
        if self.cache:
            local_path, is_temp = self.download_cached(url, md5sum)
        else:
            local_path, is_temp = self.download(url, md5sum, path)

        return locate_at(local_path, path), is_temp

    def download_cached(self, url: str, md5sum: str | None=None) -> tuple[str, bool]:
        """Download a file from a URL using the cache.

        This method assumes that the cache has been configured. Optionally, it
        raises a ChecksumError if a cached copy of a file has an MD5 mismatch,
        but will not remove the copy in that case.

        """
        download_cache = self.download_cache
        assert download_cache is not None
        if not os.path.exists(download_cache):
            raise zc.buildout.UserError(
                'The directory:\n'
                f'{download_cache!r}\n'
                "to be used as a download cache doesn't exist.\n")
        cache_dir = self.cache_dir
        assert cache_dir is not None
        if not os.path.exists(cache_dir):
            os.mkdir(cache_dir)
        cache_key = self.filename(url)
        cached_path = os.path.join(cache_dir, cache_key)

        self.logger.debug('Searching cache at %s', cache_dir)
        if os.path.exists(cached_path):
            is_temp = False
            if self.fallback:
                try:
                    _, is_temp = self.download(url, md5sum, cached_path)
                except ChecksumError:
                    raise
                except Exception:  # noqa: BLE001, S110 - deliberately silent:
                    # a failed re-download leaves the stale cache entry
                    # in place for the fallback below.
                    pass

            if not check_md5sum(cached_path, md5sum):
                raise ChecksumError(
                    'MD5 checksum mismatch for cached download '
                    f'from {url!r} at {cached_path!r}')
            self.logger.debug('Using cache file %s', cached_path)
        else:
            self.logger.debug('Cache miss; will cache %s as %s',
                              url, cached_path)
            _, is_temp = self.download(url, md5sum, cached_path)

        return cached_path, is_temp

    def download(self, url: str, md5sum: str | None=None, path: str | None=None) -> tuple[str, bool]:
        """Download a file from a URL to a given or temporary path.

        An online resource is always downloaded to a temporary file and moved
        to the specified path only after the download is complete and the
        checksum (if given) matches. If path is None, the temporary file is
        returned and the client code is responsible for cleaning it up.

        """
        # Make sure the drive letter in windows-style file paths isn't
        # interpreted as a URL scheme.
        if re.match(r"^[A-Za-z]:\\", url):
            url = 'file:' + url

        parsed_url = urlparse(url, 'file')
        url_scheme, _, url_path = parsed_url[:3]
        if url_scheme == 'file':
            self.logger.debug('Using local resource %s', url)
            if not check_md5sum(url_path, md5sum):
                raise ChecksumError(
                    f'MD5 checksum mismatch for local resource at '
                    f'{url_path!r}.')
            return locate_at(url_path, path), False

        if self.offline:
            raise zc.buildout.UserError(
                f"Couldn't download {url!r} in offline mode.\n"
                "Run buildout once in online mode with a cache directory\n"
                "configured: 'extends-cache' for configuration files,\n"
                "'download-cache' for other files; the download is then\n"
                "reused from the cache while offline.")

        self.logger.info('Downloading %s', url)
        handle, tmp_path = tempfile.mkstemp(prefix='buildout-')
        os.close(handle)
        try:
            tmp_path, _headers = urlretrieve(url, tmp_path)
            if not check_md5sum(tmp_path, md5sum):
                raise ChecksumError(
                    f'MD5 checksum mismatch downloading {url!r}')
        except OSError:
            e = sys.exc_info()[1]
            os.remove(tmp_path)
            raise zc.buildout.UserError("Error downloading extends for URL "
                              f"{url}: {e}")
        except Exception:
            os.remove(tmp_path)
            raise

        if path:
            shutil.move(tmp_path, path)
            return path, False
        else:
            return tmp_path, True

    def filename(self, url: str) -> str:
        """Determine a file name from a URL according to the configuration.

        """
        if self.hash_name:
            return md5(url.encode()).hexdigest()
        else:
            if re.match(r"^[A-Za-z]:\\", url):
                url = 'file:' + url
            parsed = urlparse(url, 'file')
            url_path = parsed[2]

            if parsed[0] == 'file':
                while True:
                    url_path, name = os.path.split(url_path)
                    if name:
                        return name
                    if not url_path:
                        break
            else:
                for name in reversed(url_path.split('/')):
                    if name:
                        return name

            url_host, url_port = parsed[-2:]
            return f'{url_host}:{url_port}'


def check_md5sum(path: str, md5sum: str | None) -> bool:
    """Tell whether the MD5 checksum of the file at path matches.

    No checksum being given is considered a match.

    """
    if md5sum is None:
        return True

    with open(path, 'rb') as f:
        checksum = md5()
        chunk = f.read(2**16)
        while chunk:
            checksum.update(chunk)
            chunk = f.read(2**16)
        return checksum.hexdigest() == md5sum


def remove(path: str) -> None:
    if os.path.exists(path):
        os.remove(path)


def locate_at(source: str, dest: str | None) -> str:
    if dest is None or realpath(dest) == realpath(source):
        return source

    if os.path.isdir(source):
        shutil.copytree(source, dest)
    else:
        try:
            os.link(source, dest)
        except (AttributeError, OSError):
            shutil.copyfile(source, dest)
    return dest
