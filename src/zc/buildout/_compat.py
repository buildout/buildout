try:
    from packaging import markers
    from packaging import specifiers
    from packaging import utils as packaging_utils
except ImportError:
    try:
        from pip._vendor.packaging import markers
        from pip._vendor.packaging import specifiers
        from pip._vendor.packaging import utils as packaging_utils
    except ImportError:
        try:
            from pkg_resources.extern.packaging import markers
            from pkg_resources.extern.packaging import specifiers
            from pkg_resources.extern.packaging import utils as packaging_utils
        except ImportError:
            from pkg_resources.packaging import markers
            from pkg_resources.packaging import specifiers
            from pkg_resources.packaging import utils as packaging_utils

__all__ = ["markers", "specifiers"]
