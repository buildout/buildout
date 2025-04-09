import re


def normalize_name(name):
    """PEP 503 normalization plus dashes as underscores.

    Taken over from importlib.metadata.
    I don't want to think about where to import this from in each
    Python version, or having it as extra dependency.

    Note that there is also packaging_utils.canonicalize_name
    which turns "foo.bar" into "foo-bar", so it is different.
    """
    return re.sub(r"[-_.]+", "-", name).lower().replace('-', '_')
