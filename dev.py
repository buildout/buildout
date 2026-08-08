# Create bin/buildout script.
# This should be called with python from a virtualenv that has all our
# dependencies already installed.
from pathlib import Path

import build  # NOQA: assert the build dependency is installed
import os
import platform
import sys


EGG_INFO_PATH = "src/zc.buildout.egg-info"
if not os.path.exists(EGG_INFO_PATH):
    print(f"ERROR: {EGG_INFO_PATH} does not exist.")
    print("You should run 'python -m build --sdist' (or 'python setup.py egg_info').")
    sys.exit(1)

# The 'bin' directory must exist.
os.makedirs('bin', exist_ok=True)

# zc.buildout must be importable in the current session.  Put 'src' on the
# path *before* importing it: importing zc.buildout also makes its vendored
# pkg_resources available as plain `pkg_resources` (setuptools >= 82 no
# longer provides it), and the pkg_resources working set is built from
# sys.path at import time, so this way it includes src/zc.buildout.egg-info.
sys.path.insert(0, "src")

# Important note: isort must NOT move these lines.
import zc.buildout.easy_install
import pkg_resources

# And then Buildout can install its own script.
zc.buildout.easy_install.scripts(
    ['zc.buildout'], pkg_resources.working_set, sys.executable, 'bin'
)

if platform.system() == "Windows":
    buildout_script = Path("bin/buildout.exe")
else:
    buildout_script = Path("bin/buildout")
if buildout_script.exists():
    print(f"SUCCESS: Generated {buildout_script} script.")
    if platform.system() != "Windows":
        # On Windows you get a UnicodeDecodeError that I don't want to debug.
        print(buildout_script.read_text())
else:
    print(f"ERROR: Generating {buildout_script} failed.")
    sys.exit(1)
