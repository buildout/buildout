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

try:
    from hashlib import md5
except ImportError:
    from md5 import new as md5

try:
    # Python 3
    from urllib.request import urlretrieve
    from urllib.parse import urlparse
except ImportError:
    # Python 2
    import base64
    from urlparse import urlparse
    from urlparse import urlunparse
    import urllib2

    def urlretrieve(url, tmp_path):
        """Work around Python issue 24599 includig basic auth support
        """
        scheme, netloc, path, params, query, frag = urlparse(url)
        auth, host = urllib2.splituser(netloc)
        if auth:
            url = urlunparse((scheme, host, path, params, query, frag))
            req = urllib2.Request(url)
            base64string = base64.encodestring(auth)[:-1]
            basic = "Basic " + base64string
            req.add_header("Authorization", basic)
        else:
            req = urllib2.Request(url)
        url_obj = urllib2.urlopen(req)
        with open(tmp_path, 'wb') as fp:
            fp.write(url_obj.read())
        return tmp_path, url_obj.info()


from zc.buildout.easy_install import realpath
import logging
import os
import os.path
import re
import shutil
import sys
import tempfile
import zc.buildout


class ChecksumError(zc.buildout.UserError):
    pass

class Download(object):
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

    def __init__(self, options={}, cache=-1, namespace=None,
                 offline=-1, fallback=False, hash_name=False, logger=None):
        self.directory = options.get('directory', '')
        self.cache = cache
        if cache == -1:
            self.cache = options.get('download-cache')
        self.namespace = namespace
        self.offline = offline
        if offline == -1:
            self.offline = (options.get('offline') == 'true'
                            or options.get('install-from-cache') == 'true')
        self.fallback = fallback
        self.hash_name = hash_name
        self.logger = logger or logging.getLogger('zc.buildout')

    @property
    def download_cache(self):
        if self.cache is not None:
            return realpath(os.path.join(self.directory, self.cache))

    @property
    def cache_dir(self):
        if self.download_cache is not None:
            return os.path.join(self.download_cache, self.namespace or '')

    def __call__(self, url, md5sum=None, path=None):
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

    def download_cached(self, url, md5sum=None):
        """Download a file from a URL using the cache.

        This method assumes that the cache has been configured. Optionally, it
        raises a ChecksumError if a cached copy of a file has an MD5 mismatch,
        but will not remove the copy in that case.

        """
        if not os.path.exists(self.download_cache):
            raise zc.buildout.UserError(
                'The directory:\n'
                '%r\n'
                "to be used as a download cache doesn't exist.\n"
                % self.download_cache)
        cache_dir = self.cache_dir
        if not os.path.exists(cache_dir):
            os.mkdir(cache_dir)
        cache_key = self.filename(url)
        cached_path = os.path.join(cache_dir, cache_key)

        self.logger.debug('Searching cache at %s' % cache_dir)
        if os.path.exists(cached_path):
            is_temp = False
            if self.fallback:
                try:
                    _, is_temp = self.download(url, md5sum, cached_path)
                except ChecksumError:
                    raise
                except Exception:
                    pass

            if not check_md5sum(cached_path, md5sum):
                raise ChecksumError(
                    'MD5 checksum mismatch for cached download '
                    'from %r at %r' % (url, cached_path))
            self.logger.debug('Using cache file %s' % cached_path)
        else:
            self.logger.debug('Cache miss; will cache %s as %s' %
                              (url, cached_path))
            _, is_temp = self.download(url, md5sum, cached_path)

        return cached_path, is_temp

    def download(self, url, md5sum=None, path=None):
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
            self.logger.debug('Using local resource %s' % url)
            if not check_md5sum(url_path, md5sum):
                raise ChecksumError(
                    'MD5 checksum mismatch for local resource at %r.' %
                    url_path)
            return locate_at(url_path, path), False

        if self.offline:
            raise zc.buildout.UserError(
                "Couldn't download %r in offline mode." % url)

        self.logger.info('Downloading %s' % url)
        handle, tmp_path = tempfile.mkstemp(prefix='buildout-')
        os.close(handle)
        try:
            tmp_path, headers = urlretrieve(url, tmp_path)
            if not check_md5sum(tmp_path, md5sum):
                raise ChecksumError(
                    'MD5 checksum mismatch downloading %r' % url)
        except IOError:
            e = sys.exc_info()[1]
            os.remove(tmp_path)
            raise zc.buildout.UserError("Error downloading extends for URL "
                              "%s: %s" % (url, e))
        except Exception:
            os.remove(tmp_path)
            raise

        if path:
            shutil.move(tmp_path, path)
            return path, False
        else:
            return tmp_path, True

    def filename(self, url):
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
            return '%s:%s' % (url_host, url_port)


def check_md5sum(path, md5sum):
    """Tell whether the MD5 checksum of the file at path matches.

    No checksum being given is considered a match.

    """
    if md5sum is None:
        return True

    f = open(path, 'rb')
    checksum = md5()
    try:
        chunk = f.read(2**16)
        while chunk:
            checksum.update(chunk)
            chunk = f.read(2**16)
        return checksum.hexdigest() == md5sum
    finally:
        f.close()


def remove(path):
    if os.path.exists(path):
        os.remove(path)


def locate_at(source, dest):
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
