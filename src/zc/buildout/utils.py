from importlib.metadata import version
from pathlib import Path

import packaging.version
import re


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


def get_source_from_pth_file(pth_file):
    """Read .pth file and extract the source path it points to.

    Lines in .pth files are either comments, import statements, or
    paths to directories.
    """
    # pth_file should be a Path object.
    text = pth_file.read_text()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('import '):
            continue
        line = Path(line)
        if line.exists():
            return line
