"""Pytest port of inline doctest functions from test_all.py — no DocTestRunner."""
import logging
import os
import re
import shutil
import subprocess
import sys
import textwrap

import pkg_resources
import pytest
import zc.buildout.easy_install
import zc.buildout.buildout
import zc.buildout.testing

from zope.testing import loggingsupport

from zc.buildout.tests.pytests.conftest import (
    assert_output,
    capture_print,
    NORMALIZERS_EASY_INSTALL,
)
from zc.buildout.tests import create_wheel

N = NORMALIZERS_EASY_INSTALL

_make_dist_setup_py = """
from setuptools import setup
setup(name=%r, version=%r,
      install_requires=%r,
      )
"""


def make_dist_that_requires(dest, name, requires=None, version=1, egg=''):
    if requires is None:
        requires = []
    os.makedirs(os.path.join(dest, name), exist_ok=True)
    with open(os.path.join(dest, name, 'setup.py'), 'w') as f:
        f.write(_make_dist_setup_py % (name, version, requires))


def prefer_final_permutation(existing, available):
    """Exercise prefer-final logic for various version permutations."""
    for d in ('existing', 'available', 'installed'):
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d)
    for version in existing:
        create_wheel('spam', version, 'existing')
        zc.buildout.easy_install.clear_index_cache()
        [dist] = list(
            zc.buildout.easy_install.install(['spam'], 'installed', ['existing'])
        )
        assert dist is not None
    for version in available:
        create_wheel('spam', version, 'available')
    zc.buildout.easy_install.clear_index_cache()
    [dist] = list(
        zc.buildout.easy_install.install(['spam'], 'installed', ['available'])
    )
    if dist.extras:
        print('downloaded', dist.version)
    else:
        print('had', dist.version)
    sys.path_importer_cache.clear()


def test_develop_w_non_setuptools_setup_scripts(easy_install_env):
    join = easy_install_env['join']
    ls = easy_install_env['ls']
    mkdir = easy_install_env['mkdir']
    print_ = easy_install_env['print_']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # We should be able to deal with setup scripts that aren't setuptools based.
    mkdir('foo')
    write('foo', 'setup.py', '\nfrom distutils.core import setup\nsetup(name="foo")\n')
    write('buildout.cfg', '\n[buildout]\ndevelop = foo\nparts =\n')
    assert_output(system(join('bin', 'buildout')), "Develop: '/sample-buildout/foo'", N)
    assert_output(capture_print(ls, 'develop-eggs'), """
-  foo.egg-link
-  zc.recipe.egg.egg-link
""", N)

def test_develop_verbose(easy_install_env):
    join = easy_install_env['join']
    ls = easy_install_env['ls']
    mkdir = easy_install_env['mkdir']
    print_ = easy_install_env['print_']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # Check how we deal with multiple times the verbose option.
    #
    #     We don't really test the output anymore: this is just too different
    #     depending on which setuptools version you use.
    mkdir('foo')
    write('foo', 'setup.py', '\nfrom setuptools import setup\nsetup(name="foo")\n')
    write('buildout.cfg', '\n[buildout]\ndevelop = foo\nparts =\n')
    assert_output(system(join('bin', 'buildout') + ' -vv'), """
Installing...
...
Making editable install of /sample-buildout/foo
...
Successfully made editable install: /sample-buildout/develop-eggs/foo.egg-link
...
""", N)
    assert_output(capture_print(ls, 'develop-eggs'), """
-  foo.egg-link
-  zc.recipe.egg.egg-link
""", N)
    assert_output(system(join('bin', 'buildout') + ' -vvv'), """
Installing...
...
Making editable install of /sample-buildout/foo
...
Successfully made editable install: /sample-buildout/develop-eggs/foo.egg-link
...
""", N)

def test_buildout_error_handling(easy_install_env):
    buildout = easy_install_env['buildout']
    os = easy_install_env['os']
    print_ = easy_install_env['print_']
    sample_buildout = easy_install_env['sample_buildout']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # Buildout error handling
    #
    # Asking for a section that doesn't exist, yields a missing section error:
    import os
    os.chdir(sample_buildout)
    import zc.buildout.buildout
    buildout = zc.buildout.buildout.Buildout('buildout.cfg', [])
    try:
        buildout['eek']
        assert False, "Expected MissingSection not raised"
    except Exception as _exc:
        assert_output(type(_exc).__name__ + ": " + str(_exc), "MissingSection: The referenced section, 'eek', was not defined.", N)
    # Asking for an option that doesn't exist, a MissingOption error is raised:
    try:
        buildout['buildout']['eek']
        assert False, "Expected MissingOption not raised"
    except Exception as _exc:
        assert_output(type(_exc).__name__ + ": " + str(_exc), 'MissingOption: Missing option: buildout:eek', N)
    # It is an error to create a variable-reference cycle:
    write(sample_buildout, 'buildout.cfg', '\n[buildout]\nparts =\nx = ${buildout:y}\ny = ${buildout:z}\nz = ${buildout:x}\n')
    assert_output(system(os.path.join(sample_buildout, 'bin', 'buildout')), """
While:
  Initializing.
  Getting section buildout.
  Initializing section buildout.
  Getting option buildout:x.
  Getting option buildout:y.
  Getting option buildout:z.
  Getting option buildout:x.
Error: Circular reference in substitutions.
""", N)
    # It is an error to use funny characters in variable references:
    write(sample_buildout, 'buildout.cfg', '\n[buildout]\ndevelop = recipes\nparts = data_dir debug\nx = ${bui$ldout:y}\n')
    assert_output(system(os.path.join(sample_buildout, 'bin', 'buildout')), """
While:
  Initializing.
  Getting section buildout.
  Initializing section buildout.
  Getting option buildout:x.
Error: The section name in substitution, ${bui$ldout:y},
has invalid characters.
""", N)
    write(sample_buildout, 'buildout.cfg', '\n[buildout]\ndevelop = recipes\nparts = data_dir debug\nx = ${buildout:y{z}\n')
    assert_output(system(os.path.join(sample_buildout, 'bin', 'buildout')), """
While:
  Initializing.
  Getting section buildout.
  Initializing section buildout.
  Getting option buildout:x.
Error: The option name in substitution, ${buildout:y{z},
has invalid characters.
""", N)
    # and too have too many or too few colons:
    write(sample_buildout, 'buildout.cfg', '\n[buildout]\ndevelop = recipes\nparts = data_dir debug\nx = ${parts}\n')
    assert_output(system(os.path.join(sample_buildout, 'bin', 'buildout')), """
While:
  Initializing.
  Getting section buildout.
  Initializing section buildout.
  Getting option buildout:x.
Error: The substitution, ${parts},
doesn't contain a colon.
""", N)
    write(sample_buildout, 'buildout.cfg', '\n[buildout]\ndevelop = recipes\nparts = data_dir debug\nx = ${buildout:y:z}\n')
    assert_output(system(os.path.join(sample_buildout, 'bin', 'buildout')), """
While:
  Initializing.
  Getting section buildout.
  Initializing section buildout.
  Getting option buildout:x.
Error: The substitution, ${buildout:y:z},
has too many colons.
""", N)
    # All parts have to have a section:
    write(sample_buildout, 'buildout.cfg', '\n[buildout]\nparts = x\n')
    assert_output(system(os.path.join(sample_buildout, 'bin', 'buildout')), """
While:
  Installing.
  Getting section x.
Error: The referenced section, 'x', was not defined.
""", N)
    # and all parts have to have a specified recipe:
    write(sample_buildout, 'buildout.cfg', '\n[buildout]\nparts = x\n\n[x]\nfoo = 1\n')
    assert_output(system(os.path.join(sample_buildout, 'bin', 'buildout')), """
While:
  Installing.
Error: Missing option: x:recipe
""", N)

def test_show_who_requires_when_there_is_a_conflict(easy_install_env):
    buildout = easy_install_env['buildout']
    print_ = easy_install_env['print_']
    sample_buildout = easy_install_env['sample_buildout']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # It's a pain when we require eggs that have requirements that are
    # incompatible. We want the error we get to tell us what is missing.
    #
    # Let's make a few develop distros, some of which have incompatible
    # requirements.
    make_dist_that_requires(sample_buildout, 'sampley', ['demoneeded ==1.0'])
    make_dist_that_requires(sample_buildout, 'samplez', ['demoneeded ==1.1'])
    # Now, let's create a buildout that requires y and z:
    write('buildout.cfg', '\n[buildout]\nparts = eggs\ndevelop = sampley samplez\nfind-links = %(link_server)s\n\n[eggs]\nrecipe = zc.recipe.egg\neggs = sampley\n       samplez\n' % easy_install_env)
    assert_output(system(buildout), """
Develop: '/sample-buildout/sampley'
Develop: '/sample-buildout/samplez'
Installing eggs.
Getting distribution for 'demoneeded==1.1'.
Got demoneeded 1.1.
Version and requirements information containing demoneeded:
  Requirement of samplez: demoneeded==1.1
  Requirement of sampley: demoneeded==1.0...
While:
  Installing eggs.
Error: There is a version conflict.
We already have: demoneeded 1.1
but sampley 1 requires 'demoneeded==1.0'.
""", N)
    # Here, we see that sampley required an older version of demoneeded. What
    # if we hadn't required sampley ourselves:
    make_dist_that_requires(sample_buildout, 'samplea', ['sampleb'])
    make_dist_that_requires(sample_buildout, 'sampleb', ['sampley', 'samplea'])
    write('buildout.cfg', '\n[buildout]\nparts = eggs\ndevelop = sampley samplez samplea sampleb\nfind-links = %(link_server)s\n\n[eggs]\nrecipe = zc.recipe.egg\neggs = samplea\n       samplez\n' % easy_install_env)
    # If we use the verbose switch, we can see where requirements are coming from:
    assert_output(system(buildout + ' -v'), """
Installing 'zc.buildout', 'wheel'...
...
Making editable install of /sample-buildout/sampley
...
Successfully made editable install: /sample-buildout/develop-eggs/sampley.egg-link
...
Making editable install of /sample-buildout/samplez
...
Successfully made editable install: /sample-buildout/develop-eggs/samplez.egg-link
...
Making editable install of /sample-buildout/samplea
...
Successfully made editable install: /sample-buildout/develop-eggs/samplea.egg-link
...
Making editable install of /sample-buildout/sampleb
...
Successfully made editable install: /sample-buildout/develop-eggs/sampleb.egg-link
...
Installing eggs.
Installing 'samplea', 'samplez'.
We have a develop egg: samplea 1
We have a develop egg: samplez 1
Getting required 'demoneeded==1.1'
  required by samplez 1.
We have the distribution that satisfies 'demoneeded==1.1'.
Getting required 'sampleb'
  required by samplea 1.
We have a develop egg: sampleb 1
Getting required 'sampley'
  required by sampleb 1.
We have a develop egg: sampley 1
Version and requirements information containing demoneeded:
  Requirement of samplez: demoneeded==1.1
  Requirement of sampley: demoneeded==1.0...
While:
  Installing eggs.
Error: There is a version conflict.
We already have: demoneeded 1.1
but sampley 1 requires 'demoneeded==1.0'.
""", N)

def test_version_conflict_rendering(easy_install_env):
    print_ = easy_install_env['print_']

    # We use the arguments passed by pkg_resources.VersionConflict to construct a
    # nice error message:
    error = pkg_resources.VersionConflict('pkg1 2.1', 'pkg1 1.0')
    ws = []
    assert_output(str(zc.buildout.easy_install.VersionConflict(error, ws)), 'There is a version conflict...', N)
    # But sometimes pkg_resources passes a nicely formatted string itself already.
    # Extracting the original arguments fails in that case, so we just show the string.
    error = pkg_resources.VersionConflict('pkg1 2.1 is simply wrong')
    ws = []
    assert_output(str(zc.buildout.easy_install.VersionConflict(error, ws)), """
There is a version conflict.
pkg1 2.1 is simply wrong
""", N)

def test_show_who_requires_missing_distributions(easy_install_env):
    buildout = easy_install_env['buildout']
    print_ = easy_install_env['print_']
    sample_buildout = easy_install_env['sample_buildout']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # When working with a lot of eggs, which require eggs recursively, it
    # can be hard to tell why we're requiring things we can't
    # find. Fortunately, buildout will tell us who's asking for something
    # that we can't find. when run in verbose mode
    make_dist_that_requires(sample_buildout, 'sampley', ['demoneeded'])
    make_dist_that_requires(sample_buildout, 'samplea', ['sampleb'])
    make_dist_that_requires(sample_buildout, 'sampleb', ['sampley', 'samplea'])
    write('buildout.cfg', '\n[buildout]\nparts = eggs\ndevelop = sampley samplea sampleb\n\n[eggs]\nrecipe = zc.recipe.egg\neggs = samplea\n')
    assert_output(system(buildout + ' -v'), """
Installing ...
Installing 'samplea'.
We have a develop egg: samplea 1
Getting required 'sampleb'
  required by samplea 1.
We have a develop egg: sampleb 1
Getting required 'sampley'
  required by sampleb 1.
We have a develop egg: sampley 1
Getting required 'demoneeded'
  required by sampley 1.
We have no distributions for demoneeded that satisfies 'demoneeded'.
...
While:
  Installing eggs.
  Getting distribution for 'demoneeded'.
Error: Couldn't find a distribution for 'demoneeded'.
""", N)

def test_show_who_requires_picked_versions(easy_install_env):
    buildout = easy_install_env['buildout']
    print_ = easy_install_env['print_']
    sample_buildout = easy_install_env['sample_buildout']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # The show-picked-versions prints the versions, but it also prints who
    # required the picked distributions.
    # We do not need to run in verbose mode for that to work:
    make_dist_that_requires(sample_buildout, 'sampley', ['demo'])
    make_dist_that_requires(sample_buildout, 'samplea', ['sampleb'])
    make_dist_that_requires(sample_buildout, 'sampleb', ['sampley', 'samplea'])
    write('buildout.cfg', '\n[buildout]\nfind-links = %(sample_eggs)s\nparts = eggs\nshow-picked-versions = true\ndevelop = sampley samplea sampleb\n\n[eggs]\nrecipe = zc.recipe.egg\neggs = samplea\n' % easy_install_env)
    assert_output(system(buildout), """
Develop: ...
...
Versions had to be automatically picked.
The following part definition lists the versions picked:
[versions]

# Required by:
# sampley==1
demo = 0.3

# Required by:
# demo==0.3
demoneeded = 1.1
""", N)

def test_comparing_saved_options_with_funny_characters(easy_install_env):
    buildout = easy_install_env['buildout']
    mkdir = easy_install_env['mkdir']
    os = easy_install_env['os']
    print_ = easy_install_env['print_']
    sample_buildout = easy_install_env['sample_buildout']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # If an option has newlines, extra/odd spaces or a %, we need to make sure
    # the comparison with the saved value works correctly.
    mkdir(sample_buildout, 'recipes')
    write(sample_buildout, 'recipes', 'debug.py', '\nclass Debug:\n    def __init__(self, buildout, name, options):\n        options[\'debug\'] = """  <zodb>\n\n  <filestorage>\n    path foo\n  </filestorage>\n\n</zodb>\n     """\n        options[\'debug1\'] = """\n<zodb>\n\n  <filestorage>\n    path foo\n  </filestorage>\n\n</zodb>\n"""\n        options[\'debug2\'] = \'  x  \'\n        options[\'debug3\'] = \'42\'\n        options[\'format\'] = \'%3d\'\n\n    def install(self):\n        with open(\'t\', \'w\') as f: f.write(\'t\')\n        return \'t\'\n\n    update = install\n')
    write(sample_buildout, 'recipes', 'setup.py', '\nfrom setuptools import setup\nsetup(\n    name = "recipes",\n    entry_points = {\'zc.buildout\': [\'default = debug:Debug\']},\n    )\n')
    write(sample_buildout, 'recipes', 'README.txt', ' ')
    write(sample_buildout, 'buildout.cfg', '\n[buildout]\ndevelop = recipes\nparts = debug\n\n[debug]\nrecipe = recipes\n')
    os.chdir(sample_buildout)
    buildout = os.path.join(sample_buildout, 'bin', 'buildout')
    assert_output(system(buildout), """
Develop: '/sample-buildout/recipes'
Installing debug.
""", N)
    # If we run the buildout again, we shouldn't get a message about
    # uninstalling anything because the configuration hasn't changed.
    assert_output(system(buildout), """
Develop: '/sample-buildout/recipes'
Updating debug.
""", N)

def test_finding_eggs_as_local_directories(easy_install_env):
    join = easy_install_env['join']
    ls = easy_install_env['ls']
    system = easy_install_env['system']
    tmpdir = easy_install_env['tmpdir']
    write = easy_install_env['write']

    # It is possible to set up find-links so that we could install from
    # a local directory that may contained unzipped eggs.
    src = tmpdir('src')
    write(src, 'setup.py', "\nfrom setuptools import setup\nsetup(name='demo', py_modules=[''],\n   zip_safe=False, version='1.0', author='bob', url='bob',\n   author_email='bob')\n")
    write(src, 't.py', '#\n')
    write(src, 'README.txt', '')
    _ = system(join('bin', 'buildout') + ' setup ' + src + ' bdist_egg')
    # Install it so it gets unzipped:
    d1 = tmpdir('d1')
    ws = zc.buildout.easy_install.install(['demo'], d1, links=[join(src, 'dist')])
    assert_output(capture_print(ls, d1), 'd  demo-1.0-py2.4.egg', N)
    # Then try to install it again:
    d2 = tmpdir('d2')
    ws = zc.buildout.easy_install.install(['demo'], d2, links=[d1])
    assert_output(capture_print(ls, d2), 'd  demo-1.0-py2.4.egg', N)

def test_create_sections_on_command_line(easy_install_env):
    buildout = easy_install_env['buildout']
    print_ = easy_install_env['print_']
    system = easy_install_env['system']
    write = easy_install_env['write']

    write('buildout.cfg', '\n[buildout]\nparts =\nx = ${foo:bar}\n')
    assert_output(system(buildout + ' foo:bar=1 -vv'), """
Installing 'zc.buildout', 'wheel', 'pip', 'setuptools'.
...
[foo]
bar = 1
...
""", N)

def test_help(easy_install_env):
    os = easy_install_env['os']
    print_ = easy_install_env['print_']
    sample_buildout = easy_install_env['sample_buildout']
    system = easy_install_env['system']

    assert_output(system(os.path.join(sample_buildout, 'bin', 'buildout') + ' -h'), """
Usage: buildout [options] [assignments] [command [command arguments]]

Options:

  -c config_file

    Specify the path to the buildout configuration file to be used.
    This defaults to the file named "buildout.cfg" in the current
    working directory.
...
  -h, --help
...
""", N)
    assert_output(system(os.path.join(sample_buildout, 'bin', 'buildout') + ' --help'), """
Usage: buildout [options] [assignments] [command [command arguments]]

Options:

  -c config_file

    Specify the path to the buildout configuration file to be used.
    This defaults to the file named "buildout.cfg" in the current
    working directory.
...
  -h, --help
...
""", N)

def test_version(easy_install_env):
    buildout = easy_install_env['buildout']
    os = easy_install_env['os']
    print_ = easy_install_env['print_']
    sample_buildout = easy_install_env['sample_buildout']
    system = easy_install_env['system']

    buildout = os.path.join(sample_buildout, 'bin', 'buildout')
    assert_output(system(buildout + ' --version'), 'buildout version ...', N)

def test_bootstrap_with_extension(easy_install_env):
    os = easy_install_env['os']
    print_ = easy_install_env['print_']
    sample_buildout = easy_install_env['sample_buildout']
    system = easy_install_env['system']
    tmpdir = easy_install_env['tmpdir']
    write = easy_install_env['write']

    # We had a problem running a bootstrap with an extension.  Let's make
    # sure it is fixed.  Basically, we don't load extensions when
    # bootstrapping.
    d = tmpdir('sample-bootstrap')
    write(d, 'buildout.cfg', '\n[buildout]\nextensions = some_awsome_extension\nparts =\n')
    os.chdir(d)
    assert_output(system(os.path.join(sample_buildout, 'bin', 'buildout') + ' bootstrap'), """
Creating directory '/sample-bootstrap/eggs/v5'.
Creating directory '/sample-bootstrap/bin'.
Creating directory '/sample-bootstrap/parts'.
Creating directory '/sample-bootstrap/develop-eggs'.
Generated script '/sample-bootstrap/bin/buildout'.
""", N)

def test_bug_92891_bootstrap_crashes_with_egg_recipe_in_buildout_section(easy_install_env):
    os = easy_install_env['os']
    print_ = easy_install_env['print_']
    sample_buildout = easy_install_env['sample_buildout']
    system = easy_install_env['system']
    tmpdir = easy_install_env['tmpdir']
    write = easy_install_env['write']

    d = tmpdir('sample-bootstrap')
    write(d, 'buildout.cfg', '\n[buildout]\nparts = buildout\neggs-directory = eggs\n\n[buildout]\nrecipe = zc.recipe.egg\neggs = zc.buildout\nscripts = buildout=buildout\n')
    os.chdir(d)
    assert_output(system(os.path.join(sample_buildout, 'bin', 'buildout') + ' bootstrap'), """
Creating directory '/sample-bootstrap/eggs/v5'.
Creating directory '/sample-bootstrap/bin'.
Creating directory '/sample-bootstrap/parts'.
Creating directory '/sample-bootstrap/develop-eggs'.
Generated script '/sample-bootstrap/bin/buildout'.
""", N)
    assert_output(system(os.path.join('bin', 'buildout')), """
Section `buildout` contains unused option(s): 'eggs' 'scripts'.
This may be an indication for either a typo in the option's name or a bug in the used recipe.
""", N)

def test_removing_eggs_from_develop_section_causes_egg_link_to_be_removed(easy_install_env):
    cd = easy_install_env['cd']
    join = easy_install_env['join']
    ls = easy_install_env['ls']
    mkdir = easy_install_env['mkdir']
    print_ = easy_install_env['print_']
    sample_buildout = easy_install_env['sample_buildout']
    system = easy_install_env['system']
    write = easy_install_env['write']

    cd(sample_buildout)
    # Create a develop egg:
    mkdir('foo')
    write('foo', 'setup.py', "\nfrom setuptools import setup\nsetup(name='foox')\n")
    write('buildout.cfg', '\n[buildout]\ndevelop = foo\nparts =\n')
    assert_output(system(join('bin', 'buildout')), "Develop: '/sample-buildout/foo'", N)
    assert_output(capture_print(ls, 'develop-eggs'), """
-  foox.egg-link
-  zc.recipe.egg.egg-link
""", N)
    # Create another:
    mkdir('bar')
    write('bar', 'setup.py', "\nfrom setuptools import setup\nsetup(name='fooy')\n")
    write('buildout.cfg', '\n[buildout]\ndevelop = foo bar\nparts =\n')
    assert_output(system(join('bin', 'buildout')), """
Develop: '/sample-buildout/foo'
Develop: '/sample-buildout/bar'
""", N)
    assert_output(capture_print(ls, 'develop-eggs'), """
-  foox.egg-link
-  fooy.egg-link
-  zc.recipe.egg.egg-link
""", N)
    # Remove one:
    write('buildout.cfg', '\n[buildout]\ndevelop = bar\nparts =\n')
    assert_output(system(join('bin', 'buildout')), "Develop: '/sample-buildout/bar'", N)
    # It is gone
    assert_output(capture_print(ls, 'develop-eggs'), """
-  fooy.egg-link
-  zc.recipe.egg.egg-link
""", N)
    # Remove the other:
    write('buildout.cfg', '\n[buildout]\nparts =\n')
    print_(system(join('bin', 'buildout')), end='')
    # All gone
    assert_output(capture_print(ls, 'develop-eggs'), '-  zc.recipe.egg.egg-link', N)

def test_add_setuptools_to_dependencies_when_namespace_packages(easy_install_env):
    join = easy_install_env['join']
    ls = easy_install_env['ls']
    mkdir = easy_install_env['mkdir']
    os = easy_install_env['os']
    print_ = easy_install_env['print_']
    sample_buildout = easy_install_env['sample_buildout']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # Often, a package depends on setuptools solely by virtue of using
    # namespace packages. In this situation, package authors often forget to
    # declare setuptools as a dependency. This is a mistake, but,
    # unfortunately, a common one that we need to work around.  If an egg
    # uses namespace packages and does not include setuptools as a dependency,
    # we will still include setuptools in the working set.  If we see this for
    # a develop egg, we will also generate a warning.
    mkdir('foo')
    mkdir('foo', 'src')
    mkdir('foo', 'src', 'stuff')
    write('foo', 'src', 'stuff', '__init__.py', "__import__('pkg_resources').declare_namespace(__name__)\n")
    mkdir('foo', 'src', 'stuff', 'foox')
    write('foo', 'src', 'stuff', 'foox', '__init__.py', '')
    write('foo', 'setup.py', "\nfrom setuptools import setup\nsetup(name='foox',\n      namespace_packages = ['stuff'],\n      package_dir = {'': 'src'},\n      packages = ['stuff', 'stuff.foox'],\n      )\n")
    write('foo', 'README.txt', '')
    write('buildout.cfg', '\n[buildout]\ndevelop = foo\nparts =\n')
    assert_output(system(join('bin', 'buildout')), """
Develop: '/sample-buildout/foo'
WARNING: Package foox at .../foo is using old style namespace packages. You should switch to native namespaces (PEP 420).
...
Some development packages are using old style namespace packages.
...
pip install horse-with-no-namespace
...
The following list shows the affected packages and their namespaces:

* foox:...
""", N)
    # Depending on the pip and setuptools versions used, the last line may either
    # be `foox: stuff` or `foox:`.
    #
    # Now, if we generate a working set using the egg link, we will get a warning
    # and we will get setuptools included in the working set.
    import logging, zope.testing.loggingsupport
    handler = zope.testing.loggingsupport.InstalledHandler('zc.buildout.easy_install', level=logging.WARNING)
    logging.getLogger('zc.buildout.easy_install').propagate = False
    def get_working_set(*project_names):
        paths = [join(sample_buildout, 'eggs', 'v5'), join(sample_buildout, 'develop-eggs')]
        return [dist.project_name for dist in zc.buildout.easy_install.working_set(project_names, sys.executable, paths)]
    _val = (get_working_set('foox'))
    assert repr(_val) == "['foox', 'setuptools']" or str(_val) == "['foox', 'setuptools']"
    assert_output(str(handler), """
zc.buildout.easy_install WARNING
  Develop distribution: foox 0.0.0
uses namespace packages but the distribution does not require setuptools.
""", N)
    handler.clear()
    # On the other hand, if we have a zipped egg, rather than a develop egg:
    os.remove(join('develop-eggs', 'foox.egg-link'))
    _ = system(join('bin', 'buildout') + ' setup foo bdist_egg')
    foox_dist = join('foo', 'dist')
    import glob
    [foox_egg] = glob.glob(join(foox_dist, 'foox-*.egg'))
    _ = shutil.copy(foox_egg, join(sample_buildout, 'eggs', 'v5'))
    assert_output(capture_print(ls, 'develop-eggs'), '-  zc.recipe.egg.egg-link', N)
    assert_output(capture_print(ls, 'eggs'), 'd  v5', N)
    assert_output(capture_print(ls, 'eggs', 'v5'), """
-  foox-0.0.0-py2.4.egg
-  packaging.egg-link
-  pip.egg-link
-  setuptools.egg-link
-  wheel.egg-link
-  zc.buildout.egg-link
""", N)
    # We do not get a warning, but we do get setuptools included in the working set:
    _val = (get_working_set('foox'))
    assert repr(_val) == "['foox', 'setuptools']" or str(_val) == "['foox', 'setuptools']"
    print_(handler, end='')
    # Likewise for an unzipped egg:
    foox_egg_basename = os.path.basename(foox_egg)
    os.remove(join(sample_buildout, 'eggs', 'v5', foox_egg_basename))
    _ = zc.buildout.easy_install.install(['foox'], join(sample_buildout, 'eggs', 'v5'), links=[foox_dist], index='file://' + foox_dist)
    assert_output(capture_print(ls, 'develop-eggs'), '-  zc.recipe.egg.egg-link', N)
    _val = (get_working_set('foox'))
    assert repr(_val) == "['foox', 'setuptools']" or str(_val) == "['foox', 'setuptools']"
    print_(handler, end='')
    # We get the same behavior if it is a dependency that uses a
    # namespace package.
    mkdir('bar')
    write('bar', 'setup.py', "\nfrom setuptools import setup\nsetup(name='bar', install_requires = ['foox'])\n")
    write('bar', 'README.txt', '')
    write('buildout.cfg', '\n[buildout]\ndevelop = foo bar\nparts =\n')
    assert_output(system(join('bin', 'buildout')), """
Develop: '/sample-buildout/foo'
WARNING: Package foox at .../foo is using old style namespace packages. You should switch to native namespaces (PEP 420).
Develop: '/sample-buildout/bar'
...
Some development packages are using old style namespace packages.
...
pip install horse-with-no-namespace
...
The following list shows the affected packages and their namespaces:

* foox:...
""", N)
    _val = (get_working_set('bar'))
    assert repr(_val) == "['bar', 'foox', 'setuptools']" or str(_val) == "['bar', 'foox', 'setuptools']"
    assert_output(str(handler), """
zc.buildout.easy_install WARNING
  Develop distribution: foox 0.0.0
uses namespace packages but the distribution does not require setuptools.
""", N)
    # On the other hand, if the distribution uses ``pkgutil.extend_path()`` to
    # implement its namespaces, even if just as fallback from the absence of
    # ``pkg_resources``, then ``setuptools`` should not be added as requirement to
    # its unzipped egg:
    foox_installed_egg = join(sample_buildout, 'eggs', 'v5', foox_egg_basename)
    namespace_init = join(foox_installed_egg, 'stuff', '__init__.py')
    write(namespace_init, "try:\n    __import__('pkg_resources').declare_namespace(__name__)\nexcept ImportError:\n    __path__ = __import__('pkgutil').extend_path(__path__, __name__)\n")
    os.remove(join('develop-eggs', 'foox.egg-link'))
    os.remove(join('develop-eggs', 'bar.egg-link'))
    _val = (get_working_set('foox'))
    assert repr(_val) == "['foox']" or str(_val) == "['foox']"
    # The same goes for packages using PEP420 namespaces
    os.remove(namespace_init)
    _val = (get_working_set('foox'))
    assert repr(_val) == "['foox']" or str(_val) == "['foox']"
    # Cleanup:
    logging.getLogger('zc.buildout.easy_install').propagate = True
    handler.uninstall()

def test_develop_preserves_existing_setup_cfg(easy_install_env):
    cat = easy_install_env['cat']
    extdemo = easy_install_env['extdemo']
    ls = easy_install_env['ls']
    mkdir = easy_install_env['mkdir']
    os = easy_install_env['os']
    sample_buildout = easy_install_env['sample_buildout']
    tmpdir = easy_install_env['tmpdir']
    write = easy_install_env['write']

    # See "Handling custom build options for extensions in develop eggs" in
    # easy_install.txt.  This will be very similar except that we'll have an
    # existing setup.cfg:
    write(extdemo, 'setup.cfg', '\n# sampe cfg file\n\n[foo]\nbar = 1\n\n[build_ext]\ndefine = X,Y\n')
    mkdir('include')
    write('include', 'extdemo.h', '\n#define EXTDEMO 42\n')
    dest = tmpdir('dest')
    _val = (zc.buildout.easy_install.develop(
  extdemo, dest,
  {'include-dirs': os.path.join(sample_buildout, 'include')}))
    assert_output(repr(_val), "'/dest/extdemo.egg-link'", N)
    assert_output(capture_print(ls, dest), '-  extdemo.egg-link', N)
    assert_output(capture_print(cat, extdemo, 'setup.cfg'), """
# sampe cfg file
[foo]
bar = 1
[build_ext]
define = X,Y
""", N)

def test_uninstall_recipes_used_for_removal(easy_install_env):
    join = easy_install_env['join']
    mkdir = easy_install_env['mkdir']
    print_ = easy_install_env['print_']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # Uninstall recipes need to be called when a part is removed too:
    mkdir('recipes')
    write('recipes', 'setup.py', '\nfrom setuptools import setup\nsetup(name=\'recipes\',\n      entry_points={\n         \'zc.buildout\': ["demo=demo:Install"],\n         \'zc.buildout.uninstall\': ["demo=demo:uninstall"],\n         })\n')
    write('recipes', 'demo.py', "\nimport sys\nclass Install:\n    def __init__(*args): pass\n    def install(self):\n        sys.stdout.write('installing\\n')\n        return ()\ndef uninstall(name, options):\n    sys.stdout.write('uninstalling\\n')\n")
    write('buildout.cfg', '\n[buildout]\ndevelop = recipes\nparts = demo\n[demo]\nrecipe = recipes:demo\n')
    assert_output(system(join('bin', 'buildout')), """
Develop: '/sample-buildout/recipes'
Installing demo.
installing
""", N)
    write('buildout.cfg', '\n[buildout]\ndevelop = recipes\nparts = demo\n[demo]\nrecipe = recipes:demo\nx = 1\n')
    assert_output(system(join('bin', 'buildout')), """
Develop: '/sample-buildout/recipes'
Uninstalling demo.
Running uninstall recipe.
uninstalling
Installing demo.
installing
""", N)
    write('buildout.cfg', '\n[buildout]\ndevelop = recipes\nparts =\n')
    assert_output(system(join('bin', 'buildout')), """
Develop: '/sample-buildout/recipes'
Uninstalling demo.
Running uninstall recipe.
uninstalling
""", N)

def test_extensions_installed_as_eggs_work_in_offline_mode(easy_install_env):
    bdist_egg = easy_install_env['bdist_egg']
    join = easy_install_env['join']
    mkdir = easy_install_env['mkdir']
    print_ = easy_install_env['print_']
    sample_buildout = easy_install_env['sample_buildout']
    system = easy_install_env['system']
    write = easy_install_env['write']

    mkdir('demo')
    write('demo', 'demo.py', "\nimport sys\ndef print_(*args):\n    sys.stdout.write(' '.join(map(str, args)) + '\\n')\ndef ext(buildout):\n    print_('ext', sorted(buildout))\n")
    write('demo', 'setup.py', '\nfrom setuptools import setup\n\nsetup(\n    name = "demo",\n    py_modules=[\'demo\'],\n    entry_points = {\'zc.buildout.extension\': [\'ext = demo:ext\']},\n    )\n')
    bdist_egg(join(sample_buildout, 'demo'), sys.executable, join(sample_buildout, 'eggs', 'v5'))
    write(sample_buildout, 'buildout.cfg', '\n[buildout]\nextensions = demo\nparts =\noffline = true\n')
    assert_output(system(join(sample_buildout, 'bin', 'buildout')), "ext ['buildout', 'versions']", N)

def test_changes_in_svn_or_git_dont_affect_sig(easy_install_env):
    join = easy_install_env['join']
    mkdir = easy_install_env['mkdir']
    print_ = easy_install_env['print_']
    sample_buildout = easy_install_env['sample_buildout']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # If we have a develop recipe, it's signature shouldn't be affected to
    # changes in .git, .svn directories.
    #
    # CVS directories used to work as well but do not anymore.
    mkdir('recipe')
    write('recipe', 'setup.py', "\nfrom setuptools import setup\nsetup(name='recipe',\n      entry_points={'zc.buildout': ['default=foo:Foo']})\n")
    write('recipe', 'foo.py', '\nclass Foo:\n    def __init__(*args): pass\n    def install(*args): return ()\n    update = install\n')
    write('buildout.cfg', '\n[buildout]\ndevelop = recipe\nparts = foo\n\n[foo]\nrecipe = recipe\n')
    assert_output(system(join(sample_buildout, 'bin', 'buildout')), """
Develop: '/sample-buildout/recipe'
Installing foo.
""", N)
    mkdir('recipe', '.git')
    mkdir('recipe', '.svn')
    assert_output(system(join(sample_buildout, 'bin', 'buildout')), """
Develop: '/sample-buildout/recipe'
Updating foo.
""", N)
    write('recipe', '.git', 'x', '1')
    write('recipe', '.svn', 'x', '1')
    assert_output(system(join(sample_buildout, 'bin', 'buildout')), """
Develop: '/sample-buildout/recipe'
Updating foo.
""", N)

def test_unicode_filename_doesnt_break_hash(easy_install_env):
    mkdir = easy_install_env['mkdir']
    write = easy_install_env['write']

    # Buildout's _dir_hash() used to break on non-ascii filenames on python 2.
    mkdir('héhé')
    write('héhé', 'héhé.py', "\nprint('Example filename from pyramid tests')\n")
    from zc.buildout.buildout import _dir_hash
    dont_care = _dir_hash('héhé')

def test_o_option_sets_offline(easy_install_env):
    join = easy_install_env['join']
    print_ = easy_install_env['print_']
    sample_buildout = easy_install_env['sample_buildout']
    system = easy_install_env['system']

    assert_output(system(join(sample_buildout, 'bin', 'buildout') + ' -vvo'), """

...
offline = true
...
""", N)

def test_recipe_upgrade(easy_install_env):
    buildout = easy_install_env['buildout']
    join = easy_install_env['join']
    mkdir = easy_install_env['mkdir']
    print_ = easy_install_env['print_']
    rmdir = easy_install_env['rmdir']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # The buildout will upgrade recipes in newest (and non-offline) mode.
    #
    # Let's create a recipe egg
    mkdir('recipe')
    write('recipe', 'recipe.py', "\nimport sys\nclass Recipe:\n    def __init__(*a): pass\n    def install(self):\n        sys.stdout.write('recipe v1\\n')\n        return ()\n    update = install\n")
    write('recipe', 'setup.py', "\nfrom setuptools import setup\nsetup(name='recipe', version='1', py_modules=['recipe'],\n      entry_points={'zc.buildout': ['default = recipe:Recipe']},\n      )\n")
    write('recipe', 'README', '')
    assert_output(system(buildout + ' setup recipe bdist_egg'), """
Running setup script 'recipe/setup.py'.
...
""", N)
    rmdir('recipe', 'build')
    # And update our buildout to use it.
    write('buildout.cfg', '\n[buildout]\nparts = foo\nfind-links = %s\n\n[foo]\nrecipe = recipe\n' % join('recipe', 'dist'))
    assert_output(system(buildout), """
Getting distribution for 'recipe'.
Got recipe 1.
Installing foo.
recipe v1
""", N)
    # Now, if we update the recipe egg:
    write('recipe', 'recipe.py', "\nimport sys\nclass Recipe:\n    def __init__(*a): pass\n    def install(self):\n        sys.stdout.write('recipe v2\\n')\n        return ()\n    update = install\n")
    write('recipe', 'setup.py', "\nfrom setuptools import setup\nsetup(name='recipe', version='2', py_modules=['recipe'],\n      entry_points={'zc.buildout': ['default = recipe:Recipe']},\n      )\n")
    assert_output(system(buildout + ' setup recipe bdist_egg'), """
Running setup script 'recipe/setup.py'.
...
""", N)
    # We won't get the update if we specify -N:
    assert_output(system(buildout + ' -N'), """
Updating foo.
recipe v1
""", N)
    # or if we use -o:
    assert_output(system(buildout + ' -o'), """
Updating foo.
recipe v1
""", N)
    # But we will if we use neither of these:
    assert_output(system(buildout), """
Getting distribution for 'recipe'.
Got recipe 2.
Uninstalling foo.
Installing foo.
recipe v2
""", N)
    # We can also select a particular recipe version:
    write('buildout.cfg', '\n[buildout]\nparts = foo\nfind-links = %s\n\n[foo]\nrecipe = recipe ==1\n' % join('recipe', 'dist'))
    assert_output(system(buildout), """
Uninstalling foo.
Installing foo.
recipe v1
""", N)

def test_update_adds_to_uninstall_list(easy_install_env):
    buildout = easy_install_env['buildout']
    cat = easy_install_env['cat']
    mkdir = easy_install_env['mkdir']
    print_ = easy_install_env['print_']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # Paths returned by the update method are added to the list of paths to
    # uninstall
    mkdir('recipe')
    write('recipe', 'setup.py', "\nfrom setuptools import setup\nsetup(name='recipe',\n      entry_points={'zc.buildout': ['default = recipe:Recipe']},\n      )\n")
    write('recipe', 'recipe.py', "\nimport os\nclass Recipe:\n    def __init__(*_): pass\n    def install(self):\n        r = ('a', 'b', 'c')\n        for p in r: os.mkdir(p)\n        return r\n    def update(self):\n        r = ('c', 'd', 'e')\n        for p in r:\n            if not os.path.exists(p):\n               os.mkdir(p)\n        return r\n")
    write('buildout.cfg', '\n[buildout]\ndevelop = recipe\nparts = foo\n\n[foo]\nrecipe = recipe\n')
    assert_output(system(buildout), """
Develop: '/sample-buildout/recipe'
Installing foo.
""", N)
    assert_output(system(buildout), """
Develop: '/sample-buildout/recipe'
Updating foo.
""", N)
    assert_output(capture_print(cat, '.installed.cfg'), """
[buildout]
...
[foo]
__buildout_installed__ = a
    b
    c
    d
    e
__buildout_signature__ = ...
""", N)

def test_log_when_there_are_not_local_distros(easy_install_env):
    link_server = easy_install_env['link_server']
    print_ = easy_install_env['print_']
    tmpdir = easy_install_env['tmpdir']

    from zope.testing.loggingsupport import InstalledHandler
    handler = InstalledHandler('zc.buildout.easy_install')
    import logging
    logger = logging.getLogger('zc.buildout.easy_install')
    old_propogate = logger.propagate
    logger.propagate = False
    dest = tmpdir('sample-install')
    import zc.buildout.easy_install
    ws = zc.buildout.easy_install.install(['demo==0.2'], dest, links=[link_server], index=link_server + 'index/')
    assert_output(str(handler), """
zc.buildout.easy_install DEBUG
  Installing 'demo==0.2'.
zc.buildout.easy_install DEBUG
  We have no distributions for demo that satisfies 'demo==0.2'.
...
""", N)
    handler.uninstall()
    logger.propagate = old_propogate

def test_internal_errors(easy_install_env):
    buildout = easy_install_env['buildout']
    mkdir = easy_install_env['mkdir']
    print_ = easy_install_env['print_']
    sample_buildout = easy_install_env['sample_buildout']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # Internal errors are clearly marked and don't generate tracebacks:
    mkdir(sample_buildout, 'recipes')
    write(sample_buildout, 'recipes', 'mkdir.py', "\nclass Mkdir:\n    def __init__(self, buildout, name, options):\n        self.name, self.options = name, options\n        options['path'] = os.path.join(\n                              buildout['buildout']['directory'],\n                              options['path'],\n                              )\n")
    write(sample_buildout, 'recipes', 'setup.py', '\nfrom setuptools import setup\nsetup(name = "recipes",\n      entry_points = {\'zc.buildout\': [\'mkdir = mkdir:Mkdir\']},\n      )\n')
    write(sample_buildout, 'buildout.cfg', '\n[buildout]\ndevelop = recipes\nparts = data-dir\n\n[data-dir]\nrecipe = recipes:mkdir\n')
    assert_output(system(buildout), """
Develop: '/sample-buildout/recipes'
While:
  Installing.
  Getting section data-dir.
  Initializing section data-dir.

An internal error occurred due to a bug in either zc.buildout or in a
recipe being used:
Traceback (most recent call last):
...
NameError: global name 'os' is not defined...
""", N)

def test_whine_about_unused_options(easy_install_env):
    buildout = easy_install_env['buildout']
    print_ = easy_install_env['print_']
    system = easy_install_env['system']
    write = easy_install_env['write']

    write('foo.py', "\nclass Foo:\n\n    def __init__(self, buildout, name, options):\n        self.name, self.options = name, options\n        options['x']\n\n    def install(self):\n        self.options['y']\n        return ()\n")
    write('setup.py', '\nfrom setuptools import setup\nsetup(name = "foo",\n      py_modules=[\'foo\'],\n      entry_points = {\'zc.buildout\': [\'default = foo:Foo\']},\n      )\n')
    write('buildout.cfg', '\n[buildout]\ndevelop = .\nparts = foo\na = 1\n\n[foo]\nrecipe = foo\nx = 1\ny = 1\nz = 1\n')
    assert_output(system(buildout), """
Develop: '/sample-buildout/.'
Section `buildout` contains unused option(s): 'a'.
This may be an indication for either a typo in the option's name or a bug in the used recipe.
Installing foo.
Section `foo` contains unused option(s): 'z'.
This may be an indication for either a typo in the option's name or a bug in the used recipe.
""", N)


def test_abnormal_exit_during_install(easy_install_env):
    buildout = easy_install_env['buildout']
    ls = easy_install_env['ls']
    mkdir = easy_install_env['mkdir']
    os = easy_install_env['os']
    system = easy_install_env['system']
    write = easy_install_env['write']
    # People sometimes hit control-c while running a builout. We need to make
    # sure that the installed database Isn't corrupted.  To test this, we'll create
    # some evil recipes that exit uncleanly:
    mkdir('recipes')
    write('recipes', 'recipes.py', '\nimport os\n\nclass Clean:\n    def __init__(*_): pass\n    def install(_): return ()\n    def update(_): pass\n\nclass EvilInstall(Clean):\n    def install(_): os._exit(1)\n\nclass EvilUpdate(Clean):\n    def update(_): os._exit(1)\n')
    write('recipes', 'setup.py', "\nimport setuptools\nsetuptools.setup(name='recipes',\n   entry_points = {\n     'zc.buildout': [\n         'clean = recipes:Clean',\n         'evil_install = recipes:EvilInstall',\n         'evil_update = recipes:EvilUpdate',\n         'evil_uninstall = recipes:Clean',\n         ],\n      },\n    )\n")
    # Now let's look at 3 cases:
    #

    # 1. We exit during installation after installing some other parts:
    write('buildout.cfg', '\n[buildout]\ndevelop = recipes\nparts = p1 p2 p3 p4\n\n[p1]\nrecipe = recipes:clean\n\n[p2]\nrecipe = recipes:clean\n\n[p3]\nrecipe = recipes:evil_install\n\n[p4]\nrecipe = recipes:clean\n')
    assert_output(system(buildout), """
Develop: '/sample-buildout/recipes'
Installing p1.
Installing p2.
Installing p3.
""", N)
    assert_output(system(buildout), """
Develop: '/sample-buildout/recipes'
Updating p1.
Updating p2.
Installing p3.
""", N)
    assert_output(system(buildout + ' buildout:parts='), """
Develop: '/sample-buildout/recipes'
Uninstalling p2.
Uninstalling p1.
""", N)


def test_abnormal_exit_while_updating(easy_install_env):
    buildout = easy_install_env['buildout']
    ls = easy_install_env['ls']
    mkdir = easy_install_env['mkdir']
    os = easy_install_env['os']
    system = easy_install_env['system']
    write = easy_install_env['write']
    # People sometimes hit control-c while running a builout. We need to make
    # sure that the installed database Isn't corrupted.  To test this, we'll create
    # some evil recipes that exit uncleanly:
    mkdir('recipes')
    write('recipes', 'recipes.py', '\nimport os\n\nclass Clean:\n    def __init__(*_): pass\n    def install(_): return ()\n    def update(_): pass\n\nclass EvilInstall(Clean):\n    def install(_): os._exit(1)\n\nclass EvilUpdate(Clean):\n    def update(_): os._exit(1)\n')
    write('recipes', 'setup.py', "\nimport setuptools\nsetuptools.setup(name='recipes',\n   entry_points = {\n     'zc.buildout': [\n         'clean = recipes:Clean',\n         'evil_install = recipes:EvilInstall',\n         'evil_update = recipes:EvilUpdate',\n         'evil_uninstall = recipes:Clean',\n         ],\n      },\n    )\n")
    # Now let's look at 3 cases:
    #

    # 2. We exit while updating:
    write('buildout.cfg', '\n[buildout]\ndevelop = recipes\nparts = p1 p2 p3 p4\n\n[p1]\nrecipe = recipes:clean\n\n[p2]\nrecipe = recipes:clean\n\n[p3]\nrecipe = recipes:evil_update\n\n[p4]\nrecipe = recipes:clean\n')
    assert_output(system(buildout), """
Develop: '/sample-buildout/recipes'
Installing p1.
Installing p2.
Installing p3.
Installing p4.
""", N)
    assert_output(system(buildout), """
Develop: '/sample-buildout/recipes'
Updating p1.
Updating p2.
Updating p3.
""", N)
    assert_output(system(buildout + ' buildout:parts='), """
Develop: '/sample-buildout/recipes'
Uninstalling p2.
Uninstalling p1.
Uninstalling p4.
Uninstalling p3.
""", N)


def test_abnormal_exit_after_uninstall(easy_install_env):
    buildout = easy_install_env['buildout']
    ls = easy_install_env['ls']
    mkdir = easy_install_env['mkdir']
    os = easy_install_env['os']
    system = easy_install_env['system']
    write = easy_install_env['write']
    # People sometimes hit control-c while running a builout. We need to make
    # sure that the installed database Isn't corrupted.  To test this, we'll create
    # some evil recipes that exit uncleanly:
    mkdir('recipes')
    write('recipes', 'recipes.py', '\nimport os\n\nclass Clean:\n    def __init__(*_): pass\n    def install(_): return ()\n    def update(_): pass\n\nclass EvilInstall(Clean):\n    def install(_): os._exit(1)\n\nclass EvilUpdate(Clean):\n    def update(_): os._exit(1)\n')
    write('recipes', 'setup.py', "\nimport setuptools\nsetuptools.setup(name='recipes',\n   entry_points = {\n     'zc.buildout': [\n         'clean = recipes:Clean',\n         'evil_install = recipes:EvilInstall',\n         'evil_update = recipes:EvilUpdate',\n         'evil_uninstall = recipes:Clean',\n         ],\n      },\n    )\n")
    # Now let's look at 3 cases:
    #

    # 3. We exit while installing or updating after uninstalling:
    write('buildout.cfg', '\n[buildout]\ndevelop = recipes\nparts = p1 p2 p3 p4\n\n[p1]\nrecipe = recipes:evil_update\n\n[p2]\nrecipe = recipes:clean\n\n[p3]\nrecipe = recipes:clean\n\n[p4]\nrecipe = recipes:clean\n')
    assert_output(system(buildout), """
Develop: '/sample-buildout/recipes'
Installing p1.
Installing p2.
Installing p3.
Installing p4.
""", N)
    write('buildout.cfg', '\n[buildout]\ndevelop = recipes\nparts = p1 p2 p3 p4\n\n[p1]\nrecipe = recipes:evil_update\n\n[p2]\nrecipe = recipes:clean\n\n[p3]\nrecipe = recipes:clean\n\n[p4]\nrecipe = recipes:clean\nx = 1\n')
    assert_output(system(buildout), """
Develop: '/sample-buildout/recipes'
Uninstalling p4.
Updating p1.
""", N)
    write('buildout.cfg', '\n[buildout]\ndevelop = recipes\nparts = p1 p2 p3 p4\n\n[p1]\nrecipe = recipes:clean\n\n[p2]\nrecipe = recipes:clean\n\n[p3]\nrecipe = recipes:clean\n\n[p4]\nrecipe = recipes:clean\n')
    assert_output(system(buildout), """
Develop: '/sample-buildout/recipes'
Uninstalling p1.
Installing p1.
Updating p2.
Updating p3.
Installing p4.
""", N)


def test_install_source_dist_with_bad_py(easy_install_env):
    buildout = easy_install_env['buildout']
    join = easy_install_env['join']
    ls = easy_install_env['ls']
    mkdir = easy_install_env['mkdir']
    print_ = easy_install_env['print_']
    system = easy_install_env['system']
    write = easy_install_env['write']

    mkdir('badegg')
    mkdir('badegg', 'badegg')
    write('badegg', 'badegg', '__init__.py', '#\\n')
    mkdir('badegg', 'badegg', 'scripts')
    write('badegg', 'badegg', 'scripts', '__init__.py', '#\\n')
    write('badegg', 'badegg', 'scripts', 'one.py', '\nreturn 1\n')
    write('badegg', 'setup.py', "\nfrom setuptools import setup, find_packages\nsetup(\n    name='badegg',\n    version='1',\n    packages = find_packages('.'),\n    zip_safe=False)\n")
    assert_output(system(buildout + ' setup badegg sdist'), """
Running setup script 'badegg/setup.py'.
...
""", N)
    dist = join('badegg', 'dist')
    write('buildout.cfg', '\n[buildout]\nparts = eggs bo\nfind-links = %(dist)s\n\n[eggs]\nrecipe = zc.recipe.egg\neggs = badegg\n\n[bo]\nrecipe = zc.recipe.egg\neggs = zc.buildout\nscripts = buildout=bo\n' % {**easy_install_env, 'dist': dist})
    assert_output(system(buildout) + '\nX', """
Installing eggs.
Getting distribution for 'badegg'.
Got badegg 1.
Installing bo.
Generated script '/sample-buildout/bin/bo'.
X
""", N)
    assert_output(capture_print(ls, 'eggs', 'v5'), """
d  badegg-1-py2.4.egg
...
""", N)
    assert_output(capture_print(ls, 'bin'), """
-  bo
-  buildout
""", N)

def test_version_requirements_in_build_honored(easy_install_env):
    link_server = easy_install_env['link_server']
    mkdir = easy_install_env['mkdir']
    os = easy_install_env['os']
    sample_buildout = easy_install_env['sample_buildout']
    tmpdir = easy_install_env['tmpdir']
    update_extdemo = easy_install_env['update_extdemo']
    write = easy_install_env['write']

    update_extdemo()
    dest = tmpdir('sample-install')
    mkdir('include')
    write('include', 'extdemo.h', '\n#define EXTDEMO 42\n')
    _val = (zc.buildout.easy_install.build(
  'extdemo ==1.4', dest,
  {'include-dirs': os.path.join(sample_buildout, 'include')},
  links=[link_server], index=link_server+'index/',
  newest=False))
    assert_output(str(_val), "['/sample-install/extdemo-1.4-py2.4-linux-i686.egg']", N)

def test_bug_105081_Specific_egg_versions_are_ignored_when_newer_eggs_are_around(easy_install_env):
    buildout = easy_install_env['buildout']
    join = easy_install_env['join']
    print_ = easy_install_env['print_']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # Buildout might ignore a specific egg requirement for a recipe:
    #
    # - Have a newer version of an egg in your eggs directory
    # - Use 'recipe==olderversion' in your buildout.cfg to request an
    #   older version
    #
    # Buildout will go and fetch the older version, but it will *use*
    # the newer version when installing a part with this recipe.
    write('buildout.cfg', '\n[buildout]\nparts = x\nfind-links = %(sample_eggs)s\n\n[x]\nrecipe = zc.recipe.egg\neggs = demo\n' % easy_install_env)
    assert_output(system(buildout), """
Installing x.
Getting distribution for 'demo'.
Got demo 0.3.
Getting distribution for 'demoneeded'.
Got demoneeded 1.1.
Generated script '/sample-buildout/bin/demo'.
""", N)
    assert_output(system(join('bin', 'demo')), '3 1', N)
    write('buildout.cfg', '\n[buildout]\nparts = x\nfind-links = %(sample_eggs)s\n\n[x]\nrecipe = zc.recipe.egg\neggs = demo ==0.1\n' % easy_install_env)
    assert_output(system(buildout), """
Uninstalling x.
Installing x.
Getting distribution for 'demo==0.1'.
Got demo 0.1.
Generated script '/sample-buildout/bin/demo'.
""", N)
    assert_output(system(join('bin', 'demo')), '1 1', N)

def test_exit_codes(easy_install_env):
    buildout = easy_install_env['buildout']
    print_ = easy_install_env['print_']
    write = easy_install_env['write']

    import subprocess
    def call(s):
        p = subprocess.Popen(s, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        p.stdin.close()
        print_(p.stdout.read().decode())
        print_('Exit:', bool(p.wait()))
        p.stdout.close()
    assert_output(capture_print(lambda: call(buildout)), """

Exit: False
""", N)
    write('buildout.cfg', '\n[buildout]\nparts = x\n')
    assert_output(capture_print(lambda: call(buildout)), """
While:
    Installing.
    Getting section x.
Error: The referenced section, 'x', was not defined.

Exit: True
""", N)
    write('setup.py', "\nfrom setuptools import setup\nsetup(name='zc.buildout.testexit',\n      py_modules=['testexitrecipe'],\n      entry_points={'zc.buildout': ['default = testexitrecipe:x']})\n")
    write('testexitrecipe.py', '\nx y\n')
    write('buildout.cfg', '\n[buildout]\nparts = x\ndevelop = .\n\n[x]\nrecipe = zc.buildout.testexit\n')
    assert_output(capture_print(lambda: call(buildout)), """
Develop: '/sample-buildout/.'
While:
    Installing.
    Getting section x.
    Initializing section x.
    Loading zc.buildout recipe entry zc.buildout.testexit:default.

An internal error occurred due to a bug in either zc.buildout or in a
recipe being used:
Traceback (most recent call last):
...
        x y
...^...
    SyntaxError...

Exit: True
""", N)

def test_bug_59270_recipes_always_start_in_buildout_dir(easy_install_env):
    join = easy_install_env['join']
    mkdir = easy_install_env['mkdir']
    os = easy_install_env['os']
    print_ = easy_install_env['print_']
    sample_buildout = easy_install_env['sample_buildout']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # Recipes can rely on running from buildout directory
    mkdir('bad_start')
    write('bad_recipe.py', "\nimport os, sys\ndef print_(*args):\n    sys.stdout.write(' '.join(map(str, args)) + '\\n')\nclass Bad:\n    def __init__(self, *_):\n        print_(os.getcwd())\n    def install(self):\n        sys.stdout.write(os.getcwd()+'\\n')\n        os.chdir('bad_start')\n        sys.stdout.write(os.getcwd()+'\\n')\n        return ()\n")
    write('setup.py', "\nfrom setuptools import setup\nsetup(name='bad.test',\n      py_modules=['bad_recipe'],\n      entry_points={'zc.buildout': ['default=bad_recipe:Bad']},)\n")
    write('buildout.cfg', '\n[buildout]\ndevelop = .\nparts = b1 b2\n[b1]\nrecipe = bad.test\n[b2]\nrecipe = bad.test\n')
    os.chdir('bad_start')
    assert_output(system(join(sample_buildout, 'bin', 'buildout') + ' -c ' + join(sample_buildout, 'buildout.cfg')), """
Develop: '/sample-buildout/.'
/sample-buildout
/sample-buildout
Installing b1.
/sample-buildout
/sample-buildout/bad_start
Installing b2.
/sample-buildout
/sample-buildout/bad_start
""", N)

def test_bug_61890_file_urls_dont_seem_to_work_in_find_dash_links(easy_install_env):
    link_server = easy_install_env['link_server']
    ls = easy_install_env['ls']
    os = easy_install_env['os']
    print_ = easy_install_env['print_']
    sample_eggs = easy_install_env['sample_eggs']
    tmpdir = easy_install_env['tmpdir']

    # This bug arises from the fact that setuptools is overly restrictive
    # about file urls, requiring that file urls pointing at directories
    # must end in a slash.
    dest = tmpdir('sample-install')
    import zc.buildout.easy_install
    sample_eggs = sample_eggs.replace(os.path.sep, '/')
    ws = zc.buildout.easy_install.install(['demo==0.2'], dest, links=['file://' + sample_eggs], index=link_server + 'index/')
    for dist in ws:
        print_(dist)
    # TODO assert: 'demoneeded 1.1\ndemo 0.2'
    assert_output(capture_print(ls, dest), """
d  demo-0.2-py2.4.egg
d  demoneeded-1.1-py2.4.egg
""", N)

def test_bug_75607_buildout_should_not_run_if_it_creates_an_empty_buildout_cfg(easy_install_env):
    buildout = easy_install_env['buildout']
    print_ = easy_install_env['print_']
    remove = easy_install_env['remove']
    system = easy_install_env['system']

    remove('buildout.cfg')
    assert_output(system(buildout), """
While:
  Initializing.
Error: Couldn't open /sample-buildout/buildout.cfg
""", N)

def test_dealing_with_extremely_insane_dependencies(easy_install_env):
    buildout = easy_install_env['buildout']
    mkdir = easy_install_env['mkdir']
    print_ = easy_install_env['print_']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # There was a problem with analysis of dependencies taking a long
    # time, in part because the analysis would get repeated every time a
    # package was encountered in a dependency list.  Now, we don't do
    # the analysis any more:
    import os
    for i in range(5):
        p = 'pack%s' % i
        deps = ['pack%s' % j for j in range(5) if j is not i]
        if i == 4:
            deps.append('pack5')
        mkdir(p)
        write(p, 'setup.py', 'from setuptools import setup\nsetup(name=%r, install_requires=%r,\n      url="u", author="a", author_email="e")\n' % (p, deps))
    write('buildout.cfg', '\n[buildout]\ndevelop = pack0 pack1 pack2 pack3 pack4\nparts = pack1\n\n[pack1]\nrecipe = zc.recipe.egg:eggs\neggs = pack0\n')
    assert_output(system(buildout), """
Develop: '/sample-buildout/pack0'
Develop: '/sample-buildout/pack1'
Develop: '/sample-buildout/pack2'
Develop: '/sample-buildout/pack3'
Develop: '/sample-buildout/pack4'
Installing pack1.
...
While:
  Installing pack1.
  Getting distribution for 'pack5'.
Error: Couldn't find a distribution for 'pack5'.
""", N)
    # However, if we run in verbose mode, we can see why packages were included:
    assert_output(system(buildout + ' -v'), """
Installing 'zc.buildout', 'wheel', 'pip', 'setuptools'.
...
Making editable install of /sample-buildout/pack0
...
Successfully made editable install: /sample-buildout/develop-eggs/pack0.egg-link
...
Making editable install of /sample-buildout/pack1
...
Successfully made editable install: /sample-buildout/develop-eggs/pack1.egg-link
...
Making editable install of /sample-buildout/pack2
...
Successfully made editable install: /sample-buildout/develop-eggs/pack2.egg-link
...
Making editable install of /sample-buildout/pack3
...
Successfully made editable install: /sample-buildout/develop-eggs/pack3.egg-link
...
Making editable install of /sample-buildout/pack4
...
Successfully made editable install: /sample-buildout/develop-eggs/pack4.egg-link
...
Installing pack1.
Installing 'pack0'.
We have a develop egg: pack0 0.0.0
Getting required 'pack4'
  required by pack0 0.0.0.
We have a develop egg: pack4 0.0.0
Getting required 'pack3'
  required by pack0 0.0.0.
  required by pack4 0.0.0.
We have a develop egg: pack3 0.0.0
Getting required 'pack2'
  required by pack0 0.0.0.
  required by pack3 0.0.0.
  required by pack4 0.0.0.
We have a develop egg: pack2 0.0.0
Getting required 'pack1'
  required by pack0 0.0.0.
  required by pack2 0.0.0.
  required by pack3 0.0.0.
  required by pack4 0.0.0.
We have a develop egg: pack1 0.0.0
Getting required 'pack5'
  required by pack4 0.0.0.
We have no distributions for pack5 that satisfies 'pack5'.
...
While:
  Installing pack1.
  Getting distribution for 'pack5'.
Error: Couldn't find a distribution for 'pack5'.
""", N)

def test_read_find_links_to_load_extensions(easy_install_env):
    buildout = easy_install_env['buildout']
    join = easy_install_env['join']
    os = easy_install_env['os']
    print_ = easy_install_env['print_']
    system = easy_install_env['system']
    tmpdir = easy_install_env['tmpdir']
    write = easy_install_env['write']

    # We'll create a wacky buildout extension that just announces itself when used:
    src = tmpdir('src')
    write(src, 'wacky_handler.py', '\nimport sys\ndef install(buildout=None):\n    sys.stdout.write("I am a wacky extension\\n")\n')
    write(src, 'setup.py', "\nfrom setuptools import setup\nsetup(name='wackyextension', version='1',\n      py_modules=['wacky_handler'],\n      entry_points = {'zc.buildout.extension':\n            ['default = wacky_handler:install']\n            },\n      )\n")
    assert_output(system(buildout + ' setup ' + src + ' bdist_egg'), """
Running setup ...
...
creating 'dist/wackyextension-1-...
""", N)
    # Now we'll create a buildout that uses this extension to load other packages:
    dist = 'file://' + join(src, 'dist').replace(os.path.sep, '/')
    write('buildout.cfg', '\n[buildout]\nparts =\nextensions = wackyextension\nfind-links = %(dist)s\n' % {**easy_install_env, 'dist': dist})
    # When we run the buildout. it will load the extension from the dist
    # directory and then use the wacky extension to load the demo package
    assert_output(system(buildout), """
Getting distribution for 'wackyextension'.
Got wackyextension 1.
I am a wacky extension
""", N)

def test_distributions_from_local_find_links_make_it_to_download_cache(easy_install_env):
    buildout = easy_install_env['buildout']
    join = easy_install_env['join']
    ls = easy_install_env['ls']
    mkdir = easy_install_env['mkdir']
    print_ = easy_install_env['print_']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # If we specify a local directory in find links, distros found there
    # need to make it to the download cache.
    mkdir('test')
    write('test', 'setup.py', "\nfrom setuptools import setup\nsetup(name='foo')\n")
    assert_output(system(buildout + ' setup test bdist_egg'), """
Running setup script 'test/setup.py'.
...
""", N)
    mkdir('cache')
    old_cache = zc.buildout.easy_install.download_cache('cache')
    assert_output(str(list(zc.buildout.easy_install.install(['foo'], 'eggs',
         links=[join('test', 'dist')]))), '[foo 0.0.0 ...', N)
    assert_output(capture_print(ls, 'cache'), '-  foo-0.0.0-py2.4.egg', N)
    _ = zc.buildout.easy_install.download_cache(old_cache)

def test_prefer_final(easy_install_env):
    # This test tests several permutations:
    #
    # Using different version numbers to work around zip importer cache problems. :(
    #
    # - With prefer final:
    #
    #     - Check that we indeed currently prefer final releases.
    _val = (zc.buildout.easy_install.prefer_final())
    assert repr(_val) == 'True' or str(_val) == 'True'
    # - no existing and newer dev available
    assert_output(capture_print(lambda: prefer_final_permutation((), [1, '2a1'])), 'downloaded 1', N)
    # - no existing and only dev available
    assert_output(capture_print(lambda: prefer_final_permutation((), ['3a1'])), 'downloaded 3a1', N)
    # - final existing and only dev acailable
    assert_output(capture_print(lambda: prefer_final_permutation([4], ['5a1'])), 'had 4', N)
    # - final existing and newer final available
    assert_output(capture_print(lambda: prefer_final_permutation([6], [7])), 'downloaded 7', N)
    # - final existing and same final available
    assert_output(capture_print(lambda: prefer_final_permutation([8], [8])), 'had 8', N)
    # - final existing and older final available
    assert_output(capture_print(lambda: prefer_final_permutation([10], [9])), 'had 10', N)
    # - only dev existing and final available
    assert_output(capture_print(lambda: prefer_final_permutation(['12a1'], [11])), 'downloaded 11', N)
    # - only dev existing and no final available newer dev available
    assert_output(capture_print(lambda: prefer_final_permutation(['13a1'], ['13a2'])), 'downloaded 13a2', N)
    # - only dev existing and no final available older dev available
    assert_output(capture_print(lambda: prefer_final_permutation(['15a1'], ['14a1'])), 'had 15a1', N)
    # - only dev existing and no final available same dev available
    assert_output(capture_print(lambda: prefer_final_permutation(['16a1'], ['16a1'])), 'had 16a1', N)
    # - Without prefer final:
    _ = zc.buildout.easy_install.prefer_final(False)
    # - no existing and newer dev available
    assert_output(capture_print(lambda: prefer_final_permutation((), [18, '19a1'])), 'downloaded 19a1', N)
    # - no existing and only dev available
    assert_output(capture_print(lambda: prefer_final_permutation((), ['20a1'])), 'downloaded 20a1', N)
    # - final existing and only dev acailable
    assert_output(capture_print(lambda: prefer_final_permutation([21], ['22a1'])), 'downloaded 22a1', N)
    # - final existing and newer final available
    assert_output(capture_print(lambda: prefer_final_permutation([23], [24])), 'downloaded 24', N)
    # - final existing and same final available
    assert_output(capture_print(lambda: prefer_final_permutation([25], [25])), 'had 25', N)
    # - final existing and older final available
    assert_output(capture_print(lambda: prefer_final_permutation([27], [26])), 'had 27', N)
    # - only dev existing and final available
    assert_output(capture_print(lambda: prefer_final_permutation(['29a1'], [28])), 'had 29a1', N)
    # - only dev existing and no final available newer dev available
    assert_output(capture_print(lambda: prefer_final_permutation(['30a1'], ['30a2'])), 'downloaded 30a2', N)
    # - only dev existing and no final available older dev available
    assert_output(capture_print(lambda: prefer_final_permutation(['32a1'], ['31a1'])), 'had 32a1', N)
    # - only dev existing and no final available same dev available
    assert_output(capture_print(lambda: prefer_final_permutation(['33a1'], ['33a1'])), 'had 33a1', N)
    _ = zc.buildout.easy_install.prefer_final(True)

def test_buildout_prefer_final_option(easy_install_env):
    buildout = easy_install_env['buildout']
    cat = easy_install_env['cat']
    print_ = easy_install_env['print_']
    remove = easy_install_env['remove']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # The prefer-final buildout option can be used for override the default
    # preference for newer distributions.
    #
    # The default is prefer-final = true:
    _val = (zc.buildout.easy_install.prefer_final())
    assert repr(_val) == 'True' or str(_val) == 'True'
    write('buildout.cfg', '\n[buildout]\nparts = eggs\nfind-links = %(link_server)s\nupdate-versions-file = versions-picked.cfg\n\n[eggs]\nrecipe = zc.recipe.egg:eggs\neggs = demo\n' % easy_install_env)
    assert_output(system(buildout), """
Installing ...
...
... written to versions-picked.cfg
""", N)
    assert_output(capture_print(cat, 'versions-picked.cfg'), """
[versions]
demo = 0.3

# Required by:
# demo==0.3
demoneeded = 1.1
""", N)
    remove('versions-picked.cfg')
    # Here we see that the final versions of demo and demoneeded are used.
    # We get the same behavior if we add prefer-final = true
    write('buildout.cfg', '\n[buildout]\nparts = eggs\nfind-links = %(link_server)s\nprefer-final = true\nupdate-versions-file = versions-picked.cfg\n\n[eggs]\nrecipe = zc.recipe.egg:eggs\neggs = demo\n' % easy_install_env)
    assert_output(system(buildout), """
Updating ...
...
... written to versions-picked.cfg
""", N)
    assert_output(capture_print(cat, 'versions-picked.cfg'), """
[versions]
demo = 0.3

# Required by:
# demo==0.3
demoneeded = 1.1
""", N)
    remove('versions-picked.cfg')
    # If we specify prefer-final = false, we'll get the newest
    # distributions:
    write('buildout.cfg', '\n[buildout]\nparts = eggs\nfind-links = %(link_server)s\nprefer-final = false\nupdate-versions-file = versions-picked.cfg\n\n[eggs]\nrecipe = zc.recipe.egg:eggs\neggs = demo\n' % easy_install_env)
    assert_output(system(buildout), """
Updating ...
...
... written to versions-picked.cfg
""", N)
    assert_output(capture_print(cat, 'versions-picked.cfg'), """
[versions]
demo = 0.4rc1

# Required by:
# demo==0.4rc1
demoneeded = 1.2rc1
""", N)
    remove('versions-picked.cfg')
    # We get an error if we specify anything but true or false:
    write('buildout.cfg', '\n[buildout]\nparts = eggs\nfind-links = %(link_server)s\nprefer-final = no\n\n[eggs]\nrecipe = zc.recipe.egg:eggs\neggs = demo\n' % easy_install_env)
    assert_output(system(buildout + ' -v'), """
While:
  Initializing.
Error: Invalid value for 'prefer-final' option: 'no'
""", N)

def test_wont_downgrade_due_to_prefer_final(easy_install_env):
    buildout = easy_install_env['buildout']
    print_ = easy_install_env['print_']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # If we install a non-final buildout version, we don't want to
    # downgrade just because we prefer-final.  If a buildout version
    # isn't specified using a versions entry, then buildout's version
    # requirement gets set to >=CURRENT_VERSION.
    write('buildout.cfg', '\n[buildout]\nparts =\n')
    [v] = [l.split('= >=', 1)[1].strip() for l in system(buildout + ' -vv').split('\n') if l.startswith('zc.buildout = >=')]
    _val = (v == pkg_resources.working_set.find(
        pkg_resources.Requirement.parse('zc.buildout')
        ).version)
    assert repr(_val) == 'True' or str(_val) == 'True'
    write('buildout.cfg', '\n[buildout]\nparts =\n[versions]\nzc.buildout = >0.1\n')
    _val = ([str(l.split('= >', 1)[1].strip())
       for l in system(buildout+' -vv').split('\n')
       if l.startswith('zc.buildout =')])
    assert repr(_val) == "['0.1']" or str(_val) == "['0.1']"
    write('buildout.cfg', '\n[buildout]\nparts =\nversions = versions\n[versions]\nzc.buildout = 43\n')
    assert_output(system(buildout), """
Getting distribution for 'zc.buildout==43'.
...
""", N)

def test_develop_with_modules(easy_install_env):
    join = easy_install_env['join']
    ls = easy_install_env['ls']
    mkdir = easy_install_env['mkdir']
    print_ = easy_install_env['print_']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # Distribution setup scripts can import modules in the distribution directory:
    mkdir('foo')
    write('foo', 'bar.py', '# empty\n')
    write('foo', 'setup.py', '\nimport bar\nfrom setuptools import setup\nsetup(name="foo")\n')
    write('buildout.cfg', '\n[buildout]\ndevelop = foo\nparts =\n')
    assert_output(system(join('bin', 'buildout')), "Develop: '/sample-buildout/foo'", N)
    assert_output(capture_print(ls, 'develop-eggs'), """
-  foo.egg-link
-  zc.recipe.egg.egg-link
""", N)

def test_dont_pick_setuptools_if_version_is_specified_when_required_by_src_dist(easy_install_env):
    buildout = easy_install_env['buildout']
    mkdir = easy_install_env['mkdir']
    print_ = easy_install_env['print_']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # When installing a source distribution, we got setuptools without
    # honoring our version specification.
    mkdir('dist')
    write('setup.py', "\nfrom setuptools import setup\nsetup(name='foo', version='1', py_modules=['foo'], zip_safe=True)\n")
    write('foo.py', '')
    _ = system(buildout + ' setup . sdist')
    write('buildout.cfg', '\n[buildout]\nparts = foo\nfind-links = dist\nversions = versions\nallow-picked-versions = false\n\n[versions]\nwtf = %s\nfoo = 1\n\n[foo]\nrecipe = zc.recipe.egg\neggs = foo\n' % '\n'.join(('%s = %s' % (d.key, d.version) for d in zc.buildout.easy_install.buildout_and_setuptools_dists)))
    assert_output(system(buildout), """
Installing foo.
Getting distribution for 'foo==1'.
Got foo 1.
""", N)

def test_pyc_and_pyo_files_have_correct_paths(easy_install_env):
    buildout = easy_install_env['buildout']
    join = easy_install_env['join']
    print_ = easy_install_env['print_']
    system = easy_install_env['system']
    write = easy_install_env['write']

    write('buildout.cfg', '\n[buildout]\nparts = eggs\nfind-links = %(link_server)s\n\n[eggs]\nrecipe = zc.recipe.egg\neggs = demo\ninterpreter = py\n' % easy_install_env)
    _ = system(buildout)
    write('t.py', "\nimport eggrecipedemo, eggrecipedemoneeded, sys\ncode = lambda f: f.__code__\nsys.stdout.write(code(eggrecipedemo.main).co_filename+'\\n')\nsys.stdout.write(code(eggrecipedemoneeded.f).co_filename+'\\n')\n")
    assert_output(system(join('bin', 'py') + ' t.py'), """
/sample-buildout/eggs/v5/demo-0.3-py2.4.egg/eggrecipedemo.py
/sample-buildout/eggs/v5/demoneeded-1.1-py2.4.egg/eggrecipedemoneeded.py
""", N)

def test_dont_mess_with_standard_dirs_with_variable_refs(easy_install_env):
    buildout = easy_install_env['buildout']
    print_ = easy_install_env['print_']
    system = easy_install_env['system']
    write = easy_install_env['write']

    write('buildout.cfg', '\n[buildout]\neggs-directory = ${buildout:directory}/develop-eggs\neggs-directory-version =\nparts =\n' % easy_install_env)
    print_(system(buildout), end='')

def test_expand_shell_patterns_in_develop_paths(easy_install_env):
    buildout = easy_install_env['buildout']
    print_ = easy_install_env['print_']
    sample_buildout = easy_install_env['sample_buildout']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # Sometimes we want to include a number of eggs in some directory as
    # develop eggs, without explicitly listing all of them in our
    # buildout.cfg
    make_dist_that_requires(sample_buildout, 'sampley')
    make_dist_that_requires(sample_buildout, 'samplez')
    # Now, let's create a buildout that has a shell pattern that matches
    # both:
    write('buildout.cfg', '\n[buildout]\nparts = eggs\ndevelop = sample*\nfind-links = %(link_server)s\n\n[eggs]\nrecipe = zc.recipe.egg\neggs = sampley\n       samplez\n' % easy_install_env)
    # We can see that both eggs were found:
    assert_output(system(buildout), """
Develop: '/sample-buildout/sampley'
Develop: '/sample-buildout/samplez'
Installing eggs.
""", N)

def test_warn_users_when_expanding_shell_patterns_yields_no_results(easy_install_env):
    buildout = easy_install_env['buildout']
    print_ = easy_install_env['print_']
    sample_buildout = easy_install_env['sample_buildout']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # Sometimes shell patterns do not match anything, so we want to warn
    # our users about it...
    make_dist_that_requires(sample_buildout, 'samplea')
    # So if we have 2 patterns, one that has a matching directory, and
    # another one that does not
    write('buildout.cfg', '\n[buildout]\nparts = eggs\ndevelop = samplea grumble*\nfind-links = %(link_server)s\n\n[eggs]\nrecipe = zc.recipe.egg\neggs = samplea\n' % easy_install_env)
    # We should get one of the eggs, and a warning for the pattern that
    # did not match anything.
    assert_output(system(buildout), """
Develop: '/sample-buildout/samplea'
Couldn't develop '/sample-buildout/grumble*' (not found)
Installing eggs.
""", N)

def test_make_sure_versions_dont_cancel_extras(easy_install_env):
    mkdir = easy_install_env['mkdir']
    sample_eggs = easy_install_env['sample_eggs']
    sdist = easy_install_env['sdist']

    # There was a bug that caused extras in requirements to be lost.
    with open('setup.py', 'w') as f:
        _ = f.write("\nfrom setuptools import setup\nsetup(name='extraversiondemo', version='1.0',\n      url='x', author='x', author_email='x',\n      extras_require=dict(foo=['demo']), py_modules=['t'])\n")
    open('README', 'w').close()
    open('t.py', 'w').close()
    sdist('.', sample_eggs)
    mkdir('dest')
    ws = zc.buildout.easy_install.install(['extraversiondemo[foo]'], 'dest', links=[sample_eggs], versions=dict(extraversiondemo='1.0'))
    _val = (sorted(dist.key for dist in ws))
    assert repr(_val) == "['demo', 'demoneeded', 'extraversiondemo']" or str(_val) == "['demo', 'demoneeded', 'extraversiondemo']"

def test_increment_buildout_options(easy_install_env):
    buildout = easy_install_env['buildout']
    print_ = easy_install_env['print_']
    system = easy_install_env['system']
    write = easy_install_env['write']

    write('b1.cfg', '\n[buildout]\nparts = p1\nx = 1\ny = a\n    b\n\n[p1]\nrecipe = zc.buildout:debug\nfoo = ${buildout:x} ${buildout:y}\n')
    write('buildout.cfg', '\n[buildout]\nextends = b1.cfg\nparts += p2\nx += 2\ny -= a\n\n[p2]\n<= p1\n')
    assert_output(system(buildout), """
Installing p1.
  foo='1\\n2 b'
  recipe='zc.buildout:debug'
Installing p2.
  foo='1\\n2 b'
  recipe='zc.buildout:debug'
""", N)

def test_increment_buildout_with_multiple_extended_files_421022(easy_install_env):
    buildout = easy_install_env['buildout']
    print_ = easy_install_env['print_']
    system = easy_install_env['system']
    write = easy_install_env['write']

    write('foo.cfg', '\n[buildout]\nfoo-option = foo\n[other]\nfoo-option = foo\n')
    write('bar.cfg', '\n[buildout]\nbar-option = bar\n[other]\nbar-option = bar\n')
    write('buildout.cfg', '\n[buildout]\nparts = p other\nextends = bar.cfg foo.cfg\nbar-option += baz\nfoo-option += ham\n\n[other]\nrecipe = zc.buildout:debug\nbar-option += baz\nfoo-option += ham\n\n[p]\nrecipe = zc.buildout:debug\nx = ${buildout:bar-option} ${buildout:foo-option}\n')
    assert_output(system(buildout), """
Installing p.
  recipe='zc.buildout:debug'
  x='bar\\nbaz foo\\nham'
Installing other.
  bar-option='bar\\nbaz'
  foo-option='foo\\nham'
  recipe='zc.buildout:debug'
""", N)

def test_increment_on_command_line(easy_install_env):
    buildout = easy_install_env['buildout']
    print_ = easy_install_env['print_']
    system = easy_install_env['system']
    write = easy_install_env['write']

    write('buildout.cfg', '\n[buildout]\nparts = p1\nx = 1\ny = a\n    b\n\n[p1]\nrecipe = zc.buildout:debug\nfoo = ${buildout:x} ${buildout:y}\n\n[p2]\n<= p1\n')
    assert_output(system(buildout + ' buildout:parts+=p2 p1:foo+=bar'), """
Installing p1.
  foo='1 a\\nb\\nbar'
  recipe='zc.buildout:debug'
Installing p2.
  foo='1 a\\nb\\nbar'
  recipe='zc.buildout:debug'
""", N)

def test_constrained_requirement(easy_install_env):
    print_ = easy_install_env['print_']

    # zc.buildout.easy_install._constrained_requirement(constraint, requirement)
    #
    # Transforms an environment by applying a constraint.
    #
    # Here's a table of examples:
    from zc.buildout.easy_install import IncompatibleConstraintError
    examples = [('x', '1', 'x==1'), ('x>1', '2', 'x==2'), ('x>3', '2', IncompatibleConstraintError), ('x>1', '>2', 'x>1,>2')]
    from zc.buildout.easy_install import _constrained_requirement
    for (o, c, e) in examples:
        try:
            o = pkg_resources.Requirement.parse(o)
            if isinstance(e, str):
                e = pkg_resources.Requirement.parse(e)
            g = _constrained_requirement(c, o)
        except IncompatibleConstraintError:
            g = IncompatibleConstraintError
        if str(g) != str(e):
            print_('failed', o, c, g, '!=', e)

def test_distutils_scripts_using_import_are_properly_parsed(easy_install_env):
    cat = easy_install_env['cat']

    # zc.buildout.easy_install._distutils_script(path, dest, script_content, initialization, rsetup):
    #
    # Creates a script for a distutils based project. In this example for a
    # hypothetical code quality checker called 'pyflint' that uses an import
    # statement to import its code.
    pyflint_script = '#!/path/to/bin/python\nimport pyflint.do_something\npyflint.do_something()\n'
    import sys
    original_executable = sys.executable
    sys.executable = 'python'
    from zc.buildout.easy_install import _distutils_script
    generated = _distutils_script("'/path/test/'", 'bin/pyflint', pyflint_script, '', '')
    if sys.platform == 'win32':
        generated == ['bin/pyflint.exe', 'bin/pyflint-script.py']
    else:
        generated == ['bin/pyflint']
    if sys.platform == 'win32':
        cat('bin/pyflint-script.py')
    else:
        cat('bin/pyflint')
    # TODO assert: "#!python\n\n\nimport sys\nsys.path[0:0] = [\n  '/path/test/',\n  ]\n\n\nimport pyflint.do"
    sys.executable = original_executable

def test_distutils_scripts_using_from_are_properly_parsed(easy_install_env):
    cat = easy_install_env['cat']

    # zc.buildout.easy_install._distutils_script(path, dest, script_content, initialization, rsetup):
    #
    # Creates a script for a distutils based project. In this example for a
    # hypothetical code quality checker called 'pyflint' that uses a from
    # statement to import its code.
    pyflint_script = '#!/path/to/bin/python\nfrom pyflint import do_something\ndo_something()\n'
    import sys
    original_executable = sys.executable
    sys.executable = 'python'
    from zc.buildout.easy_install import _distutils_script
    generated = _distutils_script("'/path/test/'", 'bin/pyflint', pyflint_script, '', '')
    if sys.platform == 'win32':
        generated == ['bin/pyflint.exe', 'bin/pyflint-script.py']
    else:
        generated == ['bin/pyflint']
    if sys.platform == 'win32':
        cat('bin/pyflint-script.py')
    else:
        cat('bin/pyflint')
    # TODO assert: "#!python\n\n\nimport sys\nsys.path[0:0] = [\n  '/path/test/',\n  ]\n\n\nfrom pyflint impo"
    sys.executable = original_executable

def test_want_new_zcrecipeegg(easy_install_env):
    join = easy_install_env['join']
    print_ = easy_install_env['print_']
    system = easy_install_env['system']
    write = easy_install_env['write']

    write('buildout.cfg', '\n[buildout]\nparts = egg\n[egg]\nrecipe = zc.recipe.egg <2dev\neggs = demo\n')
    assert_output(system(join('bin', 'buildout')), """
Getting distribution for 'zc.recipe.egg<2dev,>=2.0.6'...
While:
  Installing.
  Getting section egg.
  Initializing section egg.
  Installing recipe zc.recipe.egg <2dev.
  Getting distribution for 'zc.recipe.egg<2dev,>=2.0.6'.
Error: Couldn't find a distribution for 'zc.recipe.egg<2dev,>=2.0.6'.
""", N)

def test_macro_inheritance_bug(easy_install_env):
    join = easy_install_env['join']
    ls = easy_install_env['ls']
    print_ = easy_install_env['print_']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # There was a bug preventing a section from using another section as a macro
    # if that section was extended with macros, and both sections were listed as
    # parts (phew!).  The following contrived example demonstrates that this
    # now works.
    write('buildout.cfg', '\n[buildout]\nparts = foo bar\n[base]\nrecipe = zc.recipe.egg\n[foo]\n<=base\neggs = zc.buildout\ninterpreter = python\n[bar]\n<=foo\ninterpreter = py\n')
    assert_output(system(join('bin', 'buildout')), """
Installing foo.
...
Installing bar.
...
""", N)
    assert_output(capture_print(ls, './bin'), """
-  buildout
-  py
-  python
""", N)

def test_bootstrap_honors_relative_paths(easy_install_env):
    buildout = easy_install_env['buildout']
    cat = easy_install_env['cat']
    cd = easy_install_env['cd']
    system = easy_install_env['system']
    tmpdir = easy_install_env['tmpdir']
    write = easy_install_env['write']

    working = tmpdir('working')
    cd(working)
    write('buildout.cfg', '\n[buildout]\nparts =\nrelative-paths = true\n')
    _ = system(buildout + ' bootstrap')
    assert_output(capture_print(cat, 'bin', 'buildout'), """
#!/usr/local/bin/python2.7

import os

join = os.path.join
base = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
base = os.path.dirname(base)

import sys
sys.path[0:0] = [
  ...
  ]

import zc.buildout.buildout

if __name__ == '__main__':
    sys.exit(zc.buildout.buildout.main())
""", N)

def test_cant_use_install_from_cache_and_offline_together(easy_install_env):
    join = easy_install_env['join']
    print_ = easy_install_env['print_']
    system = easy_install_env['system']
    write = easy_install_env['write']

    write('buildout.cfg', '\n[buildout]\nparts =\noffline = true\ninstall-from-cache = true\n')
    assert_output(system(join('bin', 'buildout')), """
While:
  Initializing.
Error: install-from-cache can't be used with offline mode.
Nothing is installed, even from cache, in offline
mode, which might better be called 'no-install mode'.
""", N)

def test_error_installing_in_offline_mode_if_dont_have_needed_dist(easy_install_env):
    link_server = easy_install_env['link_server']

    import zc.buildout.easy_install
    try:
        ws = zc.buildout.easy_install.install(
            ['demo==0.2'], None,
            links=[link_server], index=link_server+'index/')
        assert False, "Expected and can't install one in offline (no-install) mode. not raised"
    except Exception as _exc:
        assert_output(type(_exc).__name__ + ": " + str(_exc), "and can't install one in offline (no-install) mode.", N)

def test_error_building_in_offline_mode_if_dont_have_needed_dist(easy_install_env):
    link_server = easy_install_env['link_server']

    try:
        zc.buildout.easy_install.build(
          'extdemo', None,
          {}, links=[link_server], index=link_server+'index/')
        assert False, "Expected and can't build one in offline (no-install) mode. not raised"
    except Exception as _exc:
        assert_output(type(_exc).__name__ + ": " + str(_exc), "and can't build one in offline (no-install) mode.", N)

def test_buildout_section_shorthand_for_command_line_assignments(easy_install_env):
    buildout = easy_install_env['buildout']
    print_ = easy_install_env['print_']
    system = easy_install_env['system']
    write = easy_install_env['write']

    write('buildout.cfg', '')
    print_(system(buildout + ' parts='), end='')

@pytest.mark.skipif(sys.platform == 'win32',
                    reason='umask on Windows is academic '
                           '(test_all.py deletes this test there too)')
def test_buildout_honors_umask(easy_install_env):
    os = easy_install_env['os']

    # For setting the executable permission, the user's umask is honored:
    orig_umask = os.umask(63)
    _val = (zc.buildout.easy_install._execute_permission() == 0o700)
    assert repr(_val) == 'True' or str(_val) == 'True'
    tmp = os.umask(18)
    _val = (zc.buildout.easy_install._execute_permission() == 0o755)
    assert repr(_val) == 'True' or str(_val) == 'True'
    tmp = os.umask(orig_umask)

def test_parse_with_section_expr(easy_install_env):
    buildout = easy_install_env['buildout']

    class Recipe:
    
        def __init__(self, buildout, *_):
            buildout.parse('\n[foo : sys.version_info[0] > 0]\nx = 1\n')
    buildout = zc.buildout.testing.Buildout()
    buildout.parse('\n[foo : sys.version_info[0] > 0]\nx = 1\n')
    assert_output(capture_print(lambda: buildout.print_options()), """
[foo]
x = 1
""", N)

def test_abi_tag_eggs(easy_install_env):
    join = easy_install_env['join']
    ls = easy_install_env['ls']
    os = easy_install_env['os']
    sample_buildout = easy_install_env['sample_buildout']
    system = easy_install_env['system']
    write = easy_install_env['write']

    write('buildout.cfg', '\n[buildout]\nfind-links = %(sample_eggs)s\nparts = abi\nabi-tag-eggs = true\n[abi]\nrecipe = zc.recipe.egg\neggs = demo\n' % easy_install_env)
    _ = system(join('bin', 'buildout'))
    from zc.buildout.pep425tags import get_abi_tag
    abi_tag = get_abi_tag()
    _val = (abi_tag in os.listdir(join(sample_buildout, 'eggs')))
    assert repr(_val) == 'False' or str(_val) == 'False'
    _val = (abi_tag in os.listdir(join(sample_buildout, 'eggs', 'v5')))
    assert repr(_val) == 'True' or str(_val) == 'True'
    assert_output(capture_print(ls, 'eggs', 'v5', abi_tag), """
d  demo-0.3-py3.7.egg
d  demoneeded-1.1-py3.7.egg
""", N)

def test_buildout_doesnt_keep_adding_itself_to_versions(easy_install_env):
    cat = easy_install_env['cat']
    join = easy_install_env['join']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # We were constantly writing to versions.cfg for buildout and setuptools
    write('buildout.cfg', '\n[buildout]\nparts =\nextends = versions.cfg\nshow-picked-versions = true\nupdate-versions-file = versions.cfg\nextends = versions.cfg\n')
    write('versions.cfg', '[versions]\n')
    _ = system(join('bin', 'buildout'))
    with open('versions.cfg') as f:
        versions = f.read()
    _ = system(join('bin', 'buildout'))
    # On the first run, some pins were added:
    assert_output(capture_print(cat, 'versions.cfg'), '[versions]', N)
    _ = system(join('bin', 'buildout'))
    _ = system(join('bin', 'buildout'))
    # Subsequent runs didn't add additional text:
    with open('versions.cfg') as f:
        versions == f.read()
