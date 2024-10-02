# Create bin/buildout script.
# This should be called with python from a virtualenv that has all our
# dependencies already installed.
from pathlib import Path

import build
import os
import pkg_resources
import sys


EGG_INFO_PATH = "src/zc.buildout.egg-info"
if not os.path.exists(EGG_INFO_PATH):
    print(f"ERROR: {EGG_INFO_PATH} does not exist.")
    print("You should run 'python -m build --sdist' (or 'python setup.py egg_info').")
    sys.exit(1)

# The 'bin' directory must exist.
os.makedirs('bin', exist_ok=True)

# zc.buildout must be importable in the current session.
pkg_resources.working_set.add_entry('src')

# Now this import should work.
# Important note: isort must NOT move this line.
import zc.buildout.easy_install

# And then Buildout can install its own script.
zc.buildout.easy_install.scripts(
    ['zc.buildout'], pkg_resources.working_set, sys.executable, 'bin'
)

buildout_script = Path("bin/buildout")
if buildout_script.exists():
    print(f"SUCCESS: Generated {buildout_script} script:")
    print(buildout_script.read_text())
else:
    print(f"ERROR: Generating {buildout_script} failed.")
    sys.exit(1)
