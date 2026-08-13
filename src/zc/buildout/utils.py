from importlib.metadata import version

import packaging.version
import re
import os


# In some cases we need to check the setuptools version to know what we can do.
SETUPTOOLS_VERSION = packaging.version.parse(version("setuptools"))
IS_SETUPTOOLS_80_PLUS = SETUPTOOLS_VERSION >= packaging.version.Version('80')


def normalize_name(name):
    """PEP 503 normalization plus dashes as underscores.

    Taken over from importlib.metadata.
    I don't want to think about where to import this from in each
    Python version, or having it as extra dependency.

    Note that there is also packaging_utils.canonicalize_name
    which turns "foo.bar" into "foo-bar", so it is different.
    """
    return re.sub(r"[-_.]+", "-", name).lower().replace('-', '_')


def get_pth_paths(loc):
    """Scan directory for .pth files and return referenced paths."""
    paths = []
    if os.path.isdir(loc):
        for name in os.listdir(loc):
            if name.endswith('.pth'):
                pth_path = os.path.join(loc, name)
                try:
                    with open(pth_path, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and not line.startswith('import '):
                                p = os.path.abspath(os.path.join(loc, line))
                                if p not in paths:
                                    paths.append(p)
                except Exception:
                    pass
    return paths
