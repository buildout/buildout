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
        from pkg_resources import _remove_md5_fragment
        from pkg_resources import Distribution

        if hasattr(Distribution, 'location'):
            return

        # prepare any Distribution built before monkeypatch
        from pkg_resources import working_set
        for dist in working_set:
            dist._location = dist.location
            dist._location_without_md5 = _remove_md5_fragment(dist.location)

        def hashcmp(self):
            without_md5 = getattr(self, '_location_without_md5', '')
            return (
                self.parsed_version,
                self.precedence,
                self.key,
                without_md5,
                self.py_version or '',
                self.platform or '',
            )

        def get_location(self):
            try:
                result = self._location
            except AttributeError:
                result = ''
            return result

        def set_location(self, l):
            self._location = l
            self._location_without_md5 = _remove_md5_fragment(l)

        setattr(Distribution, 'location', property(get_location, set_location))
        setattr(Distribution, 'hashcmp', property(hashcmp))
    except ImportError:
        return


patch_Distribution()
