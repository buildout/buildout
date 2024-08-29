try:
    # The happy path is if someone has the 'packaging' module installed .
    # We may want to add this to our own dependencies at some point.
    from packaging import markers
    from packaging import specifiers
    from packaging import utils as packaging_utils
    from packaging import version
except ImportError:
    try:
        # It is quite likely that pip has a version of packaging vendored.
        # But it is in a '_vendor' module, marked as private with an underscore,
        # so we should not rely on this: it may get moved or removed.
        from pip._vendor.packaging import markers
        from pip._vendor.packaging import specifiers
        from pip._vendor.packaging import utils as packaging_utils
        from pip._vendor.packaging import version
    except ImportError:
        try:
            # This works with the pkg_resources from setuptools 19.3
            # until at least 70, but I wonder if that may change.
            from pkg_resources.extern.packaging import markers
            from pkg_resources.extern.packaging import specifiers
            from pkg_resources.extern.packaging import utils as packaging_utils
            from pkg_resources.extern.packaging import version
        except ImportError:
            # Should work in most setuptools versions, but that may just be
            # because they import it, and could change if they restructure
            # their code.
            from pkg_resources.packaging import markers
            from pkg_resources.packaging import specifiers
            from pkg_resources.packaging import utils as packaging_utils
            from pkg_resources.packaging import version

__all__ = ["markers", "specifiers"]
