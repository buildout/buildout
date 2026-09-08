"""Pytest port of update.txt — no DocTestRunner.

Skipped on Windows: the doctest suite does not run update.txt there
either (test_all.py) — instead of "Upgraded: ..." / "Restarting.",
Windows produces "Not upgrading because not running a local buildout
command."
"""
import os
import re
import shutil
import sys
import textwrap

import pkg_resources
import pytest
import zc.buildout.easy_install
import zc.buildout.buildout
import zc.buildout.testing

from zc.buildout.tests.pytests.conftest import (
    assert_output,
    capture_print,
    NORMALIZERS_BUILDOUT,
)

pytestmark = pytest.mark.skipif(
    sys.platform.startswith('win'),
    reason='update.txt is not run on Windows in the doctest suite either')

N = NORMALIZERS_BUILDOUT + [
    (re.compile(r'(zc\.buildout|setuptools|pip)( version)? \d+[.]\d+\S*'), r'\1 V.V'),
    (re.compile(r'99[.]99'), '99.99'),
]


def test_update(update_env):
    buildout = update_env['buildout']
    cat = update_env['cat']
    cd = update_env['cd']
    ls = update_env['ls']
    mkdir = update_env['mkdir']
    new_releases = update_env['new_releases']
    print_ = update_env['print_']
    sample_buildout = update_env['sample_buildout']
    system = update_env['system']
    tmpdir = update_env['tmpdir']
    write = update_env['write']

    # Automatic Buildout Updates
    # ==========================
    #
    # When a buildout is run, one of the first steps performed is to check for
    # updates to either zc.buildout or setuptools.  To
    # demonstrate this, we've created some "new releases" of buildout and
    # setuptools in a new_releases folder:
    assert_output(capture_print(ls, new_releases), """
-  zc_buildout-91.0-py3-none-any.whl
-  zc_buildout-99.99-py3-none-any.whl
""", N)
    # Let's update the sample buildout.cfg to look in this area:
    write(sample_buildout, 'buildout.cfg',
    """
    [buildout]
    find-links = %(new_releases)s
    index = %(new_releases)s
    parts = show-versions
    develop = showversions
    
    [show-versions]
    recipe = showversions
    """ % dict(new_releases=new_releases))
    # We'll also include a recipe that echos the versions of setuptools and
    # zc.buildout used:
    mkdir(sample_buildout, 'showversions')
    write(sample_buildout, 'showversions', 'showversions.py',
    """
    import pkg_resources
    import sys
    print_ = lambda *a: sys.stdout.write(' '.join(map(str, a))+'\\n')
    
    class Recipe:
    
        def __init__(self, buildout, name, options):
            pass
    
        def install(self):
            for project in ['zc.buildout']:
                req = pkg_resources.Requirement.parse(project)
                print_(project, pkg_resources.working_set.find(req).version)
            return ()
        update = install
    """)
    write(sample_buildout, 'showversions', 'setup.py',
    """
    from setuptools import setup
    
    setup(
        name = "showversions",
        entry_points = {'zc.buildout': ['default = showversions:Recipe']},
        )
    """)
    # The installed zc.buildout version is in development mode, so it won't upgrade itself.
    assert_output(system(buildout), """
Develop:...
Installing show-versions.
zc.buildout V.V
""", N)
    # But if we run the buildout and tell it to use version 50, the buildout will upgrade itself:
    assert_output(system(buildout + ' versions:zc.buildout=91.0'), """
Getting distribution for 'zc.buildout==91.0'.
Got zc.buildout V.V
Upgraded:
  zc.buildout V.V
Restarting.
Generated script '/sample-buildout/bin/buildout'.
Develop: '/sample-buildout/showversions'
Updating show-versions.
zc.buildout V.V
""", N)
    # Now if we run the buildout without explicit version, the buildout will upgrade itself to the
    # newest version found in new releases:
    assert_output(system(buildout), """
Got zc.buildout 99.99.
Upgraded:
  zc.buildout version 99.99;
Restarting.
Generated script '/sample-buildout/bin/buildout'.
Develop: '/sample-buildout/showversions'
Updating show-versions.
zc.buildout 99.99
""", N)
    # Our buildout script has been updated to use the new eggs:
    assert_output(capture_print(cat, sample_buildout, 'bin', 'buildout'), """
#!/usr/local/bin/python2.7

import sys
sys.path[0:0] = [
  '/sample-buildout/eggs/v5/zc.buildout-99.99-pyN.N.egg',
...
  ]

import zc.buildout.buildout

if __name__ == '__main__':
    sys.exit(zc.buildout.buildout.main())
""", N)
    # Now, let's recreate the sample buildout. If we specify constraints on
    # the versions of zc.buildout and setuptools to use, running the buildout
    # will install earlier versions of these packages:
    write(sample_buildout, 'buildout.cfg',
    """
    [buildout]
    find-links = %(new_releases)s
    index = %(new_releases)s
    parts = show-versions
    develop = showversions
    
    [versions]
    zc.buildout = < 99
    
    [show-versions]
    recipe = showversions
    """ % dict(new_releases=new_releases))
    # Now we can see that we actually "upgrade" to an earlier version.
    assert_output(system(buildout), """
Upgraded:
  zc.buildout V.V
Restarting.
Generated script '/sample-buildout/bin/buildout'.
Develop: '/sample-buildout/showversions'
Updating show-versions.
zc.buildout V.V
""", N)
    # There are a number of cases, described below, in which the updates
    # don't happen.
    #
    # We won't upgrade in offline mode:
    write(sample_buildout, 'buildout.cfg',
    """
    [buildout]
    find-links = %(new_releases)s
    index = %(new_releases)s
    parts = show-versions
    develop = showversions
    
    [show-versions]
    recipe = showversions
    """ % dict(new_releases=new_releases))
    assert_output(system(buildout + ' -o'), """
Develop: '/sample-buildout/showversions'
Updating show-versions.
zc.buildout 1.0.0
""", N)
    # Or in non-newest mode:
    assert_output(system(buildout + ' -N'), """
Develop: '/sample-buildout/showversions'
Updating show-versions.
zc.buildout 1.0.0
""", N)
    # We also won't upgrade if the buildout script being run isn't in the
    # buildouts bin directory.  To see this we'll create a new buildout
    # directory:
    sample_buildout2 = tmpdir('sample_buildout2')
    write(sample_buildout2, 'buildout.cfg',
    """
    [buildout]
    find-links = %(new_releases)s
    index = %(new_releases)s
    parts =
    
    [versions]
    zc.buildout = 99.99
    """ % dict(new_releases=new_releases))
    cd(sample_buildout2)
    assert_output(system(buildout), """
Creating directory '/sample_buildout2/eggs/v5'.
Creating directory '/sample_buildout2/bin'.
Creating directory '/sample_buildout2/parts'.
Creating directory '/sample_buildout2/develop-eggs'.
Getting distribution for 'zc.buildout==99.99'.
Got zc.buildout 99.99.
Not upgrading because not running a local buildout command.
""", N)
    ls('bin')
    # .. The relative-paths option is honored:
    cd(sample_buildout)
    write(sample_buildout, 'buildout.cfg',
    """
    [buildout]
    find-links = %(new_releases)s
    index = %(new_releases)s
    parts = show-versions
    develop = showversions
    relative-paths = true
    
    [show-versions]
    recipe = showversions
    """ % dict(new_releases=new_releases))
    assert_output(system(buildout), """
Upgraded:
  zc.buildout version 99.99;
Restarting.
Generated script '/sample-buildout/bin/buildout'.
Develop: '/sample-buildout/showversions'
Section `buildout` contains unused option(s): 'relative-paths'.
This may be an indication for either a typo in the option's name or a bug in the used recipe.
Updating show-versions.
zc.buildout 99.99
""", N)
    assert_output(capture_print(cat, 'bin', 'buildout'), """
#!/usr/local/bin/python2.7

import os

join = os.path.join
base = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
base = os.path.dirname(base)

import sys
sys.path[0:0] = [
  join(base, 'eggs/v5/zc.buildout-99.99-pyN.N.egg'),
...
  ]

import zc.buildout.buildout

if __name__ == '__main__':
    sys.exit(zc.buildout.buildout.main())
""", N)
    # When buildout restarts and the restarted buildout exits with an error code,
    # the original buildout that called the second buildout also exits with that
    # error code. Otherwise build scripts can erroneously detect a successful
    # buildout run even if it failed.
    #
    # Make a recipe that fails:
    mkdir(sample_buildout, 'failrecipe')
    write(sample_buildout, 'failrecipe', 'failrecipe.py',
    """
    import pkg_resources
    import sys
    print_ = lambda *a: sys.stdout.write(' '.join(map(str, a))+'\\n')
    
    class Recipe:
    
        def __init__(self, buildout, name, options):
            sys.exit('recipe sys-exits')
    
        def install(self):
            pass
    
        update = install
    """)
    write(sample_buildout, 'failrecipe', 'setup.py',
    """
    from setuptools import setup
    
    setup(
        name = "failrecipe",
        entry_points = {'zc.buildout': ['default = failrecipe:Recipe']},
        )
    """)
    # Let's downgrade again, triggering a restart. And use the failing recipe that
    # gives us a sys.exit:
    write(sample_buildout, 'buildout.cfg',
    """
    [buildout]
    find-links = %(new_releases)s
    index = %(new_releases)s
    parts = fail
    develop = failrecipe
    
    [versions]
    zc.buildout = < 99
    
    [fail]
    recipe = failrecipe
    """ % dict(new_releases=new_releases))
    # Run the buildout:
    assert_output(system(buildout, with_exit_code=True), """
Upgraded:
  zc.buildout V.V
Restarting.
Generated script '/sample-buildout/bin/buildout'.
Develop: '/sample-buildout/failrecipe'
recipe sys-exits
EXIT CODE: 1
""", N)
