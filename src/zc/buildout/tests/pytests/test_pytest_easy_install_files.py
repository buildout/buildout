"""Pytest port of easy_install.txt, downloadcache.txt, dependencylinks.txt, allowhosts.txt, allow-unknown-extras.txt, download.txt, extends-cache.txt, testing_bugfix.txt — no DocTestRunner.

easy_install.txt is split into one test per prose section
(test_easy_install_*); the other legacy files map 1:1 to tests below."""
import sys

import pkg_resources

import zc.buildout.buildout
import zc.buildout.easy_install
import zc.buildout.errors
import zc.buildout.testing
from zc.buildout.tests.pytests.conftest import (
    NORMALIZERS_EASY_INSTALL,
    assert_output,
    capture_print,
)

N = NORMALIZERS_EASY_INSTALL


def test_easy_install_distribution_installation_newest_and_prefer_final(easy_install_env):
    get = easy_install_env['get']
    link_server = easy_install_env['link_server']
    ls = easy_install_env['ls']
    print_ = easy_install_env['print_']
    rmdir = easy_install_env['rmdir']
    tmpdir = easy_install_env['tmpdir']

    # Python API for egg and script installation
    # ==========================================
    #
    # The easy_install module provides some functions to provide support for
    # egg and script installation.  It provides functionality at the python
    # level that is similar to easy_install, with a few exceptions:
    #
    # - By default, we look for new packages *and* the packages that
    #   they depend on.  This is somewhat like (and uses) the --upgrade
    #   option of easy_install, except that we also upgrade required
    #   packages.
    #
    # - If the highest-revision package satisfying a specification is
    #   already present, then we don't try to get another one.  This saves a
    #   lot of search time in the common case that packages are pegged to
    #   specific versions.
    #
    # - If there is a develop egg that satisfies a requirement, we don't
    #   look for additional distributions.  We always give preference to
    #   develop eggs.
    #
    # - Distutils options for building extensions can be passed.
    #
    # Distribution installation
    # -------------------------
    #
    # The easy_install module provides a function, install, for installing one
    # or more packages and their dependencies.  The install function takes 2
    # positional arguments:
    #
    # - An iterable of setuptools requirement strings for the distributions
    #   to be installed, and
    #
    # - A destination directory to install to and to satisfy requirements
    #   from.  The destination directory can be None, in which case, no new
    #   distributions are downloaded and there will be an error if the
    #   needed distributions can't be found among those already installed.
    #
    # It supports a number of optional keyword arguments:
    #
    # links
    #    A sequence of URLs, file names, or directories to look for
    #    links to distributions.
    #
    # index
    #    The URL of an index server, or almost any other valid URL. :)
    #
    #    If not specified, the Python Package Index,
    #    https://pypi.org/simple/, is used.  You can specify an
    #    alternate index with this option.  If you use the links option and
    #    if the links point to the needed distributions, then the index can
    #    be anything and will be largely ignored.  In the examples, here,
    #    we'll just point to an empty directory on our link server.  This
    #    will make our examples run a little bit faster.
    #
    # path
    #    A list of additional directories to search for locally-installed
    #    distributions.
    #
    # working_set
    #    An existing working set to be augmented with additional
    #    distributions, if necessary to satisfy requirements.  This allows
    #    you to call install multiple times, if necessary, to gather
    #    multiple sets of requirements.
    #
    # newest
    #    A boolean value indicating whether to search for new distributions
    #    when already-installed distributions meet the requirement.  When
    #    this is true, the default, and when the destination directory is
    #    not None, then the install function will search for the newest
    #    distributions that satisfy the requirements.
    #
    # versions
    #    A dictionary mapping project names to version numbers to be used
    #    when selecting distributions.  This can be used to specify a set of
    #    distribution versions independent of other requirements.
    #
    # use_dependency_links
    #    A flag indicating whether to search for dependencies using the
    #    setup dependency_links metadata or not. If true, links are searched
    #    for using dependency_links in preference to other
    #    locations. Defaults to true.
    #
    # relative_paths
    #    Adjust egg paths so they are relative to the script path.  This
    #    allows scripts to work when scripts and eggs are moved, as long as
    #    they are both moved in the same way.
    #
    # allow_unknown_extras
    #     Install the requirements, even if one of them specifies an
    #     extra not provided by the distribution.
    #
    # The install method returns a working set containing the distributions
    # needed to meet the given requirements.
    #
    # We have a link server that has a number of eggs:
    assert_output(str(get(link_server)), """
<html><body>
<a href="bigdemo-0.1-py3-none-any.whl">bigdemo-0.1-py3-none-any.whl</a><br>
<a href="demo-0.1-py3-none-any.whl">demo-0.1-py3-none-any.whl</a><br>
<a href="demo-0.2-py3-none-any.whl">demo-0.2-py3-none-any.whl</a><br>
<a href="demo-0.3-py3-none-any.whl">demo-0.3-py3-none-any.whl</a><br>
<a href="demo-0.4rc1-py3-none-any.whl">demo-0.4rc1-py3-none-any.whl</a><br>
<a href="demoneeded-1.0.tar.gz">demoneeded-1.0.tar.gz</a><br>
<a href="demoneeded-1.1.tar.gz">demoneeded-1.1.tar.gz</a><br>
<a href="demoneeded-1.2rc1.tar.gz">demoneeded-1.2rc1.tar.gz</a><br>
<a href="du_zipped-1.0-pyN.N.egg">du_zipped-1.0-pyN.N.egg</a><br>
<a href="extdemo-1.4.tar.gz">extdemo-1.4.tar.gz</a><br>
<a href="index/">index/</a><br>
<a href="mixedcase-0.5.tar.gz">mixedcase-0.5.tar.gz</a><br>
<a href="other-1.0-py3-none-any.whl">other-1.0-py3-none-any.whl</a><br>
</body></html>
""", N)
    # Let's make a directory and install the demo egg to it, using the demo:
    dest = tmpdir('sample-install')
    import zc.buildout.easy_install
    ws = zc.buildout.easy_install.install(
        ['demo==0.2'], dest,
        links=[link_server], index=link_server+'index/')
    # We requested version 0.2 of the demo distribution to be installed into
    # the destination server.  We specified that we should search for links
    # on the link server and that we should use the (empty) link server
    # index directory as a package index.
    #
    # The working set contains the distributions we retrieved.
    for dist in ws:
        print_(dist)
    # TODO assert: 'demoneeded 1.1\ndemo 0.2'
    # We got demoneeded because it was a dependency of demo.
    #
    # And the actual eggs were added to the eggs directory.
    assert_output(capture_print(ls, dest), """
d  demo-0.2-py2.4.egg
d  demoneeded-1.1-py2.4.egg
""", N)
    # If we remove the version restriction on demo, but specify a false
    # value for newest, no new distributions will be installed:
    ws = zc.buildout.easy_install.install(
        ['demo'], dest, links=[link_server], index=link_server+'index/',
        newest=False)
    assert_output(capture_print(ls, dest), """
d  demo-0.2-py2.4.egg
d  demoneeded-1.1-py2.4.egg
""", N)
    # If we leave off the newest option, we'll get an update for demo:
    ws = zc.buildout.easy_install.install(
        ['demo'], dest, links=[link_server], index=link_server+'index/')
    assert_output(capture_print(ls, dest), """
d  demo-0.2-py2.4.egg
d  demo-0.3-py2.4.egg
d  demoneeded-1.1-py2.4.egg
""", N)
    # Note that we didn't get the newest versions available.  There were
    # release candidates for newer versions of both packages. By default,
    # final releases are preferred.  We can change this behavior using the
    # prefer_final function:
    _val = (zc.buildout.easy_install.prefer_final(False))
    assert repr(_val) == 'True' or str(_val) == 'True'
    # The old setting is returned.
    ws = zc.buildout.easy_install.install(
        ['demo'], dest, links=[link_server], index=link_server+'index/')
    for dist in ws:
        print_(dist)
    # TODO assert: 'demoneeded 1.2rc1\ndemo 0.4rc1'
    assert_output(capture_print(ls, dest), """
d  demo-0.2-py2.4.egg
d  demo-0.3-py2.4.egg
d  demo-0.4rc1-py2.4.egg
d  demoneeded-1.1-py2.4.egg
d  demoneeded-1.2rc1-py2.4.egg
""", N)
    # Let's put the setting back to the default.
    _val = (zc.buildout.easy_install.prefer_final(True))
    assert repr(_val) == 'False' or str(_val) == 'False'
    # We can supply additional distributions.  We can also supply
    # specifications for distributions that would normally be found via
    # dependencies.  We might do this to specify a specific version.
    ws = zc.buildout.easy_install.install(
        ['demo', 'other', 'demoneeded==1.0'], dest,
        links=[link_server], index=link_server+'index/')
    for dist in ws:
        print_(dist)
    # TODO assert: 'demoneeded 1.0\nother 1.0\ndemo 0.3'
    assert_output(capture_print(ls, dest), """
d  demo-0.2-py2.4.egg
d  demo-0.3-py2.4.egg
d  demo-0.4rc1-py2.4.egg
d  demoneeded-1.0-py2.4.egg
d  demoneeded-1.1-py2.4.egg
d  demoneeded-1.2rc1-py2.4.egg
d  other-1.0-py2.4.egg
""", N)
    rmdir(dest)


def test_easy_install_distribution_installation_unknown_extras(easy_install_env):
    link_server = easy_install_env['link_server']
    ls = easy_install_env['ls']
    rmdir = easy_install_env['rmdir']
    tmpdir = easy_install_env['tmpdir']
    dest = tmpdir('sample-install')

    # Unknown extras
    # --------------
    #
    # Attempting to install a requirement with an extra it doesn't provide
    # is an error.
    try:
        _ = zc.buildout.easy_install.install(
            ['demo[unknown_extra]'], dest, links=[link_server],
            index=link_server+'index/')
        assert False, "Expected UserError not raised"
    except Exception as _exc:  # noqa: BLE001 - the class
        # and message are pinned by the assertion below
        assert_output(str(_exc), "Couldn't find the required extra...", N)
    # We can pass the ``allow_unknown_extras`` argument to force the
    # installation to proceed.
    _ = zc.buildout.easy_install.install(
        ['demo[unknown_extra]'], dest, links=[link_server],
        index=link_server+'index/',
        allow_unknown_extras=True)
    import os
    names = sorted(os.listdir(dest))
    if zc.buildout.easy_install.installer() == 'uv':
        # uv resolves the full dependency closure in one compile, so
        # demoneeded rides along; the legacy unknown-extra quirk that
        # dropped the base requirements has no replay there.
        assert any(name.startswith('demoneeded-1.1-') for name in names)
    else:
        assert_output(capture_print(ls, dest), 'd  demo-0.3-py2.4.egg', N)
    rmdir(dest)


def test_easy_install_distribution_installation_case_issues(easy_install_env):
    get = easy_install_env['get']
    link_server = easy_install_env['link_server']
    ls = easy_install_env['ls']
    print_ = easy_install_env['print_']
    rmdir = easy_install_env['rmdir']
    tmpdir = easy_install_env['tmpdir']
    dest = tmpdir('sample-install')

    # Case issues
    # -----------
    #
    # Let's install an egg with case naming issues.
    # Specifically, the sdist file is lower case while the name of the package is uppercase.
    #
    # Let's enable server logging to check that the lower case file is downloaded.
    _ = get(link_server + 'enable_server_logging')
    # TODO assert: 'GET 200 /enable_server_logging'
    ws = zc.buildout.easy_install.install(
        ['MIXEDCASE'], dest,
        links=[link_server], index=link_server+'index/')
    # TODO assert: 'GET 404 /index/mixedcase/\nGET 200 /mixedcase-0.5.tar.gz\nGET '
    # Let's check that the uppercase dist is installed.
    # setuptools 75.8.1+ reports the name in all lowercase, earlier versions showed it in uppercase.
    # So we compare lowercase.
    for dist in ws:
        print_(str(dist).lower())
    # TODO assert: 'demoneeded 1.1\nmixedcase 0.5'
    assert_output(capture_print(ls, dest, lowercase_and_sort_output=True), """
d  demoneeded-1.1-py2.4.egg
d  mixedcase-0.5-pyN.N.egg
""", N)
    # And cleanup.
    _ = get(link_server + 'disable_server_logging')
    rmdir(dest)


def test_easy_install_specifying_versions(easy_install_env):
    link_server = easy_install_env['link_server']
    tmpdir = easy_install_env['tmpdir']
    dest = tmpdir('sample-install')

    # Specifying version information independent of requirements
    # ----------------------------------------------------------
    #
    # Sometimes it's useful to specify version information independent of
    # normal requirements specifications.  For example, a buildout may need
    # to lock down a set of versions, without having to put put version
    # numbers in setup files or part definitions.  If a dictionary is passed
    # to the install function, mapping project names to version numbers,
    # then the versions numbers will be used.
    ws = zc.buildout.easy_install.install(
        ['demo'], dest, links=[link_server], index=link_server+'index/',
        versions = {'demo': '0.2', 'demoneeded': '1.0'})
    _val = ([d.version for d in ws])
    assert repr(_val) == "['1.0', '0.2']" or str(_val) == "['1.0', '0.2']"
    # In this example, we specified a version for demoneeded, even though we
    # didn't define a requirement for it.  The versions specified apply to
    # dependencies as well as the specified requirements.
    #
    # If we specify a version that's incompatible with a requirement, then
    # we'll get an error:
    from zope.testing.loggingsupport import InstalledHandler
    handler = InstalledHandler('zc.buildout.easy_install')
    import logging
    logging.getLogger('zc.buildout.easy_install').propagate = False
    try:
        ws = zc.buildout.easy_install.install(
            ['demo >0.2'], dest, links=[link_server],
            index=link_server+'index/',
            versions = {'demo': '0.2', 'demoneeded': '1.0'})
        assert False, "Expected IncompatibleConstraintError not raised"
    except Exception as _exc:  # noqa: BLE001 - the class
        # and message are pinned by the assertion below
        assert_output(str(_exc), "The requirement ('demo>0.2') is not allowed by your [versions] constraint (0.2)", N)
    assert_output(str(handler), """
zc.buildout.easy_install DEBUG
  Installing 'demo >0.2'.
zc.buildout.easy_install INFO
  Version and requirements information containing demo:
  [versions] constraint on demo: 0.2
  Base installation request: 'demo >0.2'
""", N)
    handler.clear()
    # If no versions are specified, a debugging message will be output
    # reporting that a version was picked automatically:
    ws = zc.buildout.easy_install.install(
        ['demo'], dest, links=[link_server], index=link_server+'index/',
        )
    assert_output(str(handler), """
zc.buildout.easy_install DEBUG
  Installing 'demo'.
zc.buildout.easy_install INFO
  Getting distribution for 'demo'.
zc.buildout.easy_install DEBUG
  Fetching demo 0.3 from: http://.../demo-0.3-py3-none-any.whl
zc.buildout.easy_install DEBUG
  Turning dist demo 0.3 (.../demo-0.3-py3-none-any.whl) into egg, and moving to eggs dir /sample-install).
zc.buildout.easy_install DEBUG
  Calling pip install for .whl on .../demo-0.3-py3-none-any.whl
zc.buildout.easy_install DEBUG
  Running pip install:...
...
zc.buildout.easy_install DEBUG
  Egg for demo 0.3 installed at .../demo-0.3-pyN.N.egg
zc.buildout.easy_install INFO
  Got demo 0.3.
zc.buildout.easy_install DEBUG
  Picked: demo = 0.3
zc.buildout.easy_install DEBUG
  Getting required 'demoneeded'
zc.buildout.easy_install DEBUG
    required by demo 0.3.
zc.buildout.easy_install INFO
  Getting distribution for 'demoneeded'.
zc.buildout.easy_install DEBUG
  Fetching demoneeded 1.1 from: http://.../demoneeded-1.1.tar.gz
zc.buildout.easy_install DEBUG
  Turning dist demoneeded 1.1 (.../demoneeded-1.1.tar.gz) into egg, and moving to eggs dir /sample-install).
zc.buildout.easy_install DEBUG
  Calling pip install for .gz on .../demoneeded-1.1.tar.gz
zc.buildout.easy_install DEBUG
  Running pip install:...
...
zc.buildout.easy_install DEBUG
  Egg for demoneeded 1.1 installed at .../demoneeded-1.1-pyN.N.egg
zc.buildout.easy_install INFO
  Got demoneeded 1.1.
zc.buildout.easy_install DEBUG
  Picked: demoneeded = 1.1
""", N)
    handler.uninstall()
    logging.getLogger('zc.buildout.easy_install').propagate = True
    # We can request that we get an error if versions are picked:
    _val = (zc.buildout.easy_install.allow_picked_versions(False))
    assert repr(_val) == 'True' or str(_val) == 'True'
    # (The old setting is returned.)
    try:
        ws = zc.buildout.easy_install.install(
            ['demo'], dest, links=[link_server], index=link_server+'index/',
            )
        assert False, "Expected OR set `allow-picked-versions = true`. not raised"
    except Exception as _exc:  # noqa: BLE001 - the class
        # and message are pinned by the assertion below
        assert_output(str(_exc), 'OR set `allow-picked-versions = true`.', N)
    _val = (zc.buildout.easy_install.allow_picked_versions(True))
    assert repr(_val) == 'False' or str(_val) == 'False'
    # The function default_versions can be used to get and set default
    # version information to be used when no version information is passes.
    # If called with an argument, it sets the default versions:
    _val = (zc.buildout.easy_install.default_versions({'demoneeded': '1'}))
    assert_output(str(_val), '{...}', N)
    # It always returns the previous default versions.  If called without an
    # argument, it simply returns the default versions without changing
    # them:
    _val = (zc.buildout.easy_install.default_versions())
    assert repr(_val) == "{'demoneeded': '1'}" or str(_val) == "{'demoneeded': '1'}"
    # So with the default versions set, we'll get the requested version even
    # if the versions option isn't used:
    ws = zc.buildout.easy_install.install(
        ['demo'], dest, links=[link_server], index=link_server+'index/',
        )
    _val = ([d.version for d in ws])
    assert repr(_val) == "['0.3', '1.0']" or str(_val) == "['0.3', '1.0']"
    # Of course, we can unset the default versions by passing an empty
    # dictionary:
    _val = (zc.buildout.easy_install.default_versions({}))
    assert repr(_val) == "{'demoneeded': '1'}" or str(_val) == "{'demoneeded': '1'}"
    ws = zc.buildout.easy_install.install(
        ['demo'], dest, links=[link_server], index=link_server+'index/',
        )
    _val = ([d.version for d in ws])
    assert repr(_val) == "['0.3', '1.1']" or str(_val) == "['0.3', '1.1']"


def test_easy_install_use_dependency_links(easy_install_env):
    get = easy_install_env['get']
    link_server = easy_install_env['link_server']
    rmdir = easy_install_env['rmdir']
    start_server = easy_install_env['start_server']
    tmpdir = easy_install_env['tmpdir']

    # Dependency links
    # ----------------
    #
    # Setuptools allows metadata that describes where to search for package
    # dependencies. This option is called dependency_links. Buildout has its
    # own notion of where to look for dependencies, but it also uses the
    # setup tools dependency_links information if it's available.
    #
    # Let's demo this by creating an egg that specifies dependency_links.
    #
    # To begin, let's create a new egg repository. This repository hold a
    # newer version of the 'demoneeded' egg than the sample repository does.
    repoloc = tmpdir('repo')
    from zc.buildout.tests import create_wheel
    create_wheel('demoneeded', '1.2', repoloc)
    link_server2 = start_server(repoloc)
    # Turn on logging on this server so that we can see when eggs are pulled
    # from it.
    _ = get(link_server2 + 'enable_server_logging')
    # TODO assert: 'GET 200 /enable_server_logging'
    # Now we can create an egg that specifies that its dependencies are
    # found on this server.
    repoloc = tmpdir('repo2')
    create_wheel('hasdeps', '1.0', repoloc,
                 install_requires = "'demoneeded'",
                 dependency_links = [link_server2])
    # Let's add the egg to another repository.
    link_server3 = start_server(repoloc)
    # Now let's install the egg.
    example_dest = tmpdir('example-install')
    if zc.buildout.easy_install.installer() == 'uv':
        # uv-deprecated: uv discovers no dependency_links metadata,
        # so with link_server3 alone the closure lacks demoneeded
        # and the install reports the missing distribution.
        try:
            _ = zc.buildout.easy_install.install(
                ['hasdeps'], example_dest,
                links=[link_server3], index=link_server3+'index/')
        except zc.buildout.errors.MissingDistribution:
            pass
        else:
            raise AssertionError('unexpectedly installed hasdeps')
    else:
        _ = zc.buildout.easy_install.install(
            ['hasdeps'], example_dest,
            links=[link_server3], index=link_server3+'index/')
    # TODO assert: 'GET 200 /\nGET 200 /demoneeded-1.2-py3-none-any.whl'
    # The server logs show that the dependency was retrieved from the server
    # specified in the dependency_links.
    #
    # Now let's see what happens if we provide two different ways to retrieve
    # the dependencies.
    rmdir(example_dest)
    example_dest = tmpdir('example-install')
    _ = zc.buildout.easy_install.install(
        ['hasdeps'], example_dest, index=link_server+'index/',
        links=[link_server, link_server3])
    # TODO assert: 'GET 200 /\nGET 200 /demoneeded-1.2-py3-none-any.whl'
    # Once again the dependency is fetched from the logging server even
    # though it is also available from the non-logging server. This is
    # because the version on the logging server is newer and buildout
    # normally chooses the newest egg available.
    #
    # If you wish to control where dependencies come from regardless of
    # dependency_links setup metadata use the 'use_dependency_links' option
    # to zc.buildout.easy_install.install().
    rmdir(example_dest)
    example_dest = tmpdir('example-install')
    _ = zc.buildout.easy_install.install(
        ['hasdeps'], example_dest, index=link_server+'index/',
        links=[link_server, link_server3],
        use_dependency_links=False)
    # Notice that this time the dependency egg is not fetched from the
    # logging server. When you specify not to use dependency_links, eggs
    # will only be searched for using the links you explicitly provide.
    #
    # Another way to control this option is with the
    # zc.buildout.easy_install.use_dependency_links() function. This
    # function sets the default behavior for the zc.buildout.easy_install()
    # function.
    _val = (zc.buildout.easy_install.use_dependency_links(False))
    assert repr(_val) == 'True' or str(_val) == 'True'
    # The function returns its previous setting.
    rmdir(example_dest)
    example_dest = tmpdir('example-install')
    _ = zc.buildout.easy_install.install(
        ['hasdeps'], example_dest, index=link_server+'index/',
        links=[link_server, link_server3])
    # It can be overridden by passing a keyword argument to the install
    # function.
    rmdir(example_dest)
    example_dest = tmpdir('example-install')
    _ = zc.buildout.easy_install.install(
        ['hasdeps'], example_dest, index=link_server+'index/',
        links=[link_server, link_server3],
        use_dependency_links=True)
    # TODO assert: 'GET 200 /demoneeded-1.2-py3-none-any.whl'
    # To return the dependency_links behavior to normal call the function again.
    _val = (zc.buildout.easy_install.use_dependency_links(True))
    assert repr(_val) == 'False' or str(_val) == 'False'
    rmdir(example_dest)
    example_dest = tmpdir('example-install')
    zc.buildout.easy_install.install(
        ['hasdeps'], example_dest, index=link_server+'index/',
        links=[link_server, link_server3])
    # TODO assert: 'GET 200 /demoneeded-1.2-py3-none-any.whl'


def test_easy_install_script_generation(easy_install_env):
    cat = easy_install_env['cat']
    join = easy_install_env['join']
    link_server = easy_install_env['link_server']
    ls = easy_install_env['ls']
    system = easy_install_env['system']
    tmpdir = easy_install_env['tmpdir']
    write = easy_install_env['write']
    dest = tmpdir('sample-install')
    zc.buildout.easy_install.install(
        ['demo'], dest, links=[link_server], index=link_server+'index/',
        versions={'demo': '0.2', 'demoneeded': '1.0'})
    zc.buildout.easy_install.install(
        ['demo'], dest, links=[link_server], index=link_server+'index/')
    ws = zc.buildout.easy_install.install(
        ['demo'], dest, links=[link_server], index=link_server+'index/')

    # Script generation
    # -----------------
    #
    # The easy_install module provides support for creating scripts from
    # eggs.  It provides a function similar to setuptools except that it
    # provides facilities for baking a script's path into the script.  This
    # has two advantages:
    #
    # - The eggs to be used by a script are not chosen at run time, making
    #   startup faster and, more importantly, deterministic.
    #
    # - The script doesn't have to import pkg_resources because the logic
    #   that pkg_resources would execute at run time is executed at
    #   script-creation time.
    #
    # The scripts method can be used to generate scripts. Let's create a
    # destination directory for it to place them in:
    bin = tmpdir('bin')
    # Now, we'll use the scripts method to generate scripts in this directory
    # from the demo egg:
    import sys
    scripts = zc.buildout.easy_install.scripts(
        ['demo'], ws, sys.executable, bin)
    # the three arguments we passed were:
    #
    # 1. A sequence of distribution requirements.  These are of the same
    #    form as setuptools requirements.  Here we passed a single
    #    requirement, for the version 0.1 demo distribution.
    #
    # 2. A working set,
    #
    # 3. The destination directory.
    #
    # The bin directory now contains a generated script:
    assert_output(capture_print(ls, bin), '-  demo', N)
    # The return value is a list of the scripts generated:
    import os
    import sys
    _val = (scripts == ([os.path.join(bin, 'demo.exe'),
             os.path.join(bin, 'demo-script.py')]
            if sys.platform == 'win32'
            else [os.path.join(bin, 'demo')]))
    assert repr(_val) == 'True' or str(_val) == 'True'
    # Note that in Windows, 2 files are generated for each script.  A script
    # file, ending in '-script.py', and an exe file that allows the script
    # to be invoked directly without having to specify the Python
    # interpreter and without having to provide a '.py' suffix.
    #
    # The demo script run the entry point defined in the demo egg:
    assert_output(capture_print(cat, bin, 'demo'), """
#!/usr/local/bin/python2.7

import sys
sys.path[0:0] = [
  '/sample-install/demo-0.3-py2.4.egg',
  '/sample-install/demoneeded-1.1-py2.4.egg',
  ]

import eggrecipedemo

if __name__ == '__main__':
    sys.exit(eggrecipedemo.main())
""", N)
    # Some things to note:
    #
    # - The demo and demoneeded eggs are added to the beginning of sys.path.
    #
    # - The module for the script entry point is imported and the entry
    #   point, in this case, 'main', is run.
    #
    # Rather than requirement strings, you can pass tuples containing 3
    # strings:
    #
    #   - A script name,
    #
    #   - A module,
    #
    #   - An attribute expression for an entry point within the module.
    #
    # For example, we could have passed entry point information directly
    # rather than passing a requirement:
    scripts = zc.buildout.easy_install.scripts(
        [('demo', 'eggrecipedemo', 'main')], ws,
        sys.executable, bin)
    assert_output(capture_print(cat, bin, 'demo'), """
#!/usr/local/bin/python2.7

import sys
sys.path[0:0] = [
  '/sample-install/demo-0.3-py2.4.egg',
  '/sample-install/demoneeded-1.1-py2.4.egg',
  ]

import eggrecipedemo

if __name__ == '__main__':
    sys.exit(eggrecipedemo.main())
""", N)
    # Passing entry-point information directly is handy when using eggs (or
    # distributions) that don't declare their entry points, such as
    # distributions that aren't based on setuptools.
    #
    # The interpreter keyword argument can be used to generate a script that can
    # be used to invoke the Python interactive interpreter with the path set
    # based on the working set.  This generated script can also be used to
    # run other scripts with the path set on the working set:
    scripts = zc.buildout.easy_install.scripts(
        ['demo'], ws, sys.executable, bin, interpreter='py')
    assert_output(capture_print(ls, bin), """
-  demo
-  py
""", N)
    _val = (scripts == ([os.path.join(bin, 'demo.exe'),
             os.path.join(bin, 'demo-script.py'),
             os.path.join(bin, 'py.exe'),
             os.path.join(bin, 'py-script.py')]
            if sys.platform == 'win32'
            else [os.path.join(bin, 'demo'),
                  os.path.join(bin, 'py')]))
    assert repr(_val) == 'True' or str(_val) == 'True'
    # The py script simply runs the Python interactive interpreter with
    # the path set:
    assert_output(capture_print(cat, bin, 'py'), """
#!/usr/local/bin/python2.7

import sys

sys.path[0:0] = [
  '/sample-install/demo-0.3-pyN.N.egg',
  '/sample-install/demoneeded-1.1-pyN.N.egg',
  ]

_interactive = True
if len(sys.argv) > 1:
    # The Python interpreter wrapper allows only some of the options that a
    # "regular" Python interpreter accepts.
    _options, _args = __import__("getopt").getopt(sys.argv[1:], 'Iic:m:')
    _interactive = False
    for (_opt, _val) in _options:
        if _opt == '-i':
            _interactive = True
        elif _opt == '-c':
            exec(_val)
        elif _opt == '-m':
            sys.argv[1:] = _args
            _args = []
            __import__("runpy").run_module(
                 _val, {}, "__main__", alter_sys=True)
        elif _opt == '-I':
            # Allow yet silently ignore the `-I` option. The original behaviour
            # for this option is to create an isolated Python runtime. It was
            # deemed acceptable to allow the option here as this Python wrapper
            # is isolated from the system Python already anyway.
            # The specific use-case that led to this change is how the Python
            # language extension for Visual Studio Code calls the Python
            # interpreter when initializing the extension.
            pass

    if _args:
        sys.argv[:] = _args
        __file__ = _args[0]
        del _options, _args
        with open(__file__) as __file__f:
            exec(compile(__file__f.read(), __file__, "exec"))

if _interactive:
    del _interactive
    __import__("code").interact(banner="", local=globals())
""", N)
    # If invoked with a script name and arguments, it will run that script, instead.
    write('ascript', r'''
    "demo doc"
    import sys
    print_ = lambda *a: sys.stdout.write(' '.join(map(str, a))+'\n')
    print_(sys.argv)
    print_((__name__, __file__, __doc__))
    ''')
    assert_output(system(join(bin, 'py') + ' ascript a b c'), """
['ascript', 'a', 'b', 'c']
('__main__', 'ascript', 'demo doc')
""", N)
    # You can also use the -m option to run a module:
    assert_output(system(join(bin, 'py') + ' -m pdb'), 'usage: ...pdb...', N)
    assert_output(system(join(bin, 'py') + ' -m pdb what'), 'Error: what does not exist', N)
    # An interpreter can also be generated without other eggs:
    scripts = zc.buildout.easy_install.scripts(
        [], pkg_resources.WorkingSet([]), sys.executable, bin, interpreter='py')
    assert_output(capture_print(cat, bin, 'py'), """
#!/usr/local/bin/python2.7

import sys

sys.path[0:0] = [

  ]
...
""", N)
    # An additional argument can be passed to define which scripts to install
    # and to provide script names. The argument is a dictionary mapping
    # original script names to new script names.
    bin = tmpdir('bin2')
    scripts = zc.buildout.easy_install.scripts(
        ['demo'], ws, sys.executable, bin, {'demo': 'run'})
    _val = (scripts == ([os.path.join(bin, 'run.exe'),
             os.path.join(bin, 'run-script.py')]
            if sys.platform == 'win32'
            else [os.path.join(bin, 'run')]))
    assert repr(_val) == 'True' or str(_val) == 'True'
    assert_output(capture_print(ls, bin), '-  run', N)
    assert_output(system(os.path.join(bin, 'run')), '3 1', N)
    # The scripts that are generated are made executable:
    if sys.platform == 'win32':
        os.access(os.path.join(bin, 'run.exe'), os.X_OK)
    else:
        os.access(os.path.join(bin, 'run'), os.X_OK)
    # Including extra paths in scripts
    # --------------------------------
    #
    # We can pass a keyword argument, extra paths, to cause additional paths
    # to be included in the a generated script:
    foo = tmpdir('foo')
    scripts = zc.buildout.easy_install.scripts(
       ['demo'], ws, sys.executable, bin, {'demo': 'run'},
       extra_paths=[foo])
    assert_output(capture_print(cat, bin, 'run'), """
#!/usr/local/bin/python2.7

import sys
sys.path[0:0] = [
  '/sample-install/demo-0.3-py2.4.egg',
  '/sample-install/demoneeded-1.1-py2.4.egg',
  '/foo',
  ]

import eggrecipedemo

if __name__ == '__main__':
    sys.exit(eggrecipedemo.main())
""", N)
    # Providing script arguments
    # --------------------------
    #
    # An "argument" keyword argument can be used to pass arguments to an
    # entry point.  The value passed is a source string to be placed between the
    # parentheses in the call:
    scripts = zc.buildout.easy_install.scripts(
       ['demo'], ws, sys.executable, bin, {'demo': 'run'},
       arguments='1, 2')
    assert_output(capture_print(cat, bin, 'run'), """
#!/usr/local/bin/python2.7
import sys
sys.path[0:0] = [
  '/sample-install/demo-0.3-py2.4.egg',
  '/sample-install/demoneeded-1.1-py2.4.egg',
  ]

import eggrecipedemo

if __name__ == '__main__':
    sys.exit(eggrecipedemo.main(1, 2))
""", N)
    # Passing initialization code
    # ---------------------------
    #
    # You can also pass script initialization code:
    scripts = zc.buildout.easy_install.scripts(
       ['demo'], ws, sys.executable, bin, {'demo': 'run'},
       arguments='1, 2',
       initialization='import os\nos.chdir("foo")',
       interpreter='py')
    assert_output(capture_print(cat, bin, 'run'), """
#!/usr/local/bin/python2.7
import sys
sys.path[0:0] = [
  '/sample-install/demo-0.3-py2.4.egg',
  '/sample-install/demoneeded-1.1-py2.4.egg',
  ]

import os
os.chdir("foo")

import eggrecipedemo

if __name__ == '__main__':
    sys.exit(eggrecipedemo.main(1, 2))
""", N)
    # It will be included in interpreters too:
    assert_output(capture_print(cat, bin, 'py'), """
#!/usr/local/bin/python2.7

import sys

sys.path[0:0] = [
  '/sample-install/demo-0.3-py3.3.egg',
  '/sample-install/demoneeded-1.1-py3.3.egg',
  ]

import os
os.chdir("foo")


_interactive = True
...
""", N)


def test_easy_install_relative_paths(easy_install_env):
    cat = easy_install_env['cat']
    join = easy_install_env['join']
    link_server = easy_install_env['link_server']
    mkdir = easy_install_env['mkdir']
    system = easy_install_env['system']
    tmpdir = easy_install_env['tmpdir']

    # Relative paths
    # --------------
    #
    # Sometimes, you want to be able to move a buildout directory around and
    # have scripts still work without having to rebuild them.  We can
    # control this using the relative_paths option to install.  You need
    # to pass a common base directory of the scripts and eggs:
    bo = tmpdir('bo')
    ba = tmpdir('ba')
    mkdir(bo, 'eggs')
    mkdir(bo, 'bin')
    mkdir(bo, 'other')
    ws = zc.buildout.easy_install.install(
        ['demo'], join(bo, 'eggs'), links=[link_server],
        index=link_server+'index/')
    _ = zc.buildout.easy_install.scripts(
       ['demo'], ws, sys.executable, join(bo, 'bin'), {'demo': 'run'},
       extra_paths=[ba, join(bo, 'bar'), bo],
       interpreter='py',
       relative_paths=bo)
    assert_output(capture_print(cat, bo, 'bin', 'run'), """
#!/usr/local/bin/python2.7

import os

join = os.path.join
base = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
base = os.path.dirname(base)

import sys
sys.path[0:0] = [
  join(base, 'eggs/demoneeded-1.1-pyN.N.egg'),
  join(base, 'eggs/demo-0.3-pyN.N.egg'),
  '/ba',
  join(base, 'bar'),
  base,
  ]

import eggrecipedemo

if __name__ == '__main__':
    sys.exit(eggrecipedemo.main())
""", N)
    # Note that the extra path we specified that was outside the directory
    # passed as relative_paths wasn't converted to a relative path.
    #
    # Of course, running the script works:
    assert_output(system(join(bo, 'bin', 'run')), '3 1', N)
    # We specified an interpreter and its paths are adjusted too:
    assert_output(capture_print(cat, bo, 'bin', 'py'), """
#!/usr/local/bin/python2.7

import os

join = os.path.join
base = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
base = os.path.dirname(base)

import sys

sys.path[0:0] = [
  join(base, 'eggs/demoneeded-1.1-pyN.N.egg'),
  join(base, 'eggs/demo-0.3-pyN.N.egg'),
  '/ba',
  join(base, 'bar'),
  base,
  ]


_interactive = True
if len(sys.argv) > 1:
    # The Python interpreter wrapper allows only some of the options that a
    # "regular" Python interpreter accepts.
    _options, _args = __import__("getopt").getopt(sys.argv[1:], 'Iic:m:')
    _interactive = False
    for (_opt, _val) in _options:
        if _opt == '-i':
            _interactive = True
        elif _opt == '-c':
            exec(_val)
        elif _opt == '-m':
            sys.argv[1:] = _args
            _args = []
            __import__("runpy").run_module(
                 _val, {}, "__main__", alter_sys=True)
        elif _opt == '-I':
            # Allow yet silently ignore the `-I` option. The original behaviour
            # for this option is to create an isolated Python runtime. It was
            # deemed acceptable to allow the option here as this Python wrapper
            # is isolated from the system Python already anyway.
            # The specific use-case that led to this change is how the Python
            # language extension for Visual Studio Code calls the Python
            # interpreter when initializing the extension.
            pass

    if _args:
        sys.argv[:] = _args
        __file__ = _args[0]
        del _options, _args
        with open(__file__) as __file__f:
            exec(compile(__file__f.read(), __file__, "exec"))

if _interactive:
    del _interactive
    __import__("code").interact(banner="", local=globals())
""", N)
    # # Installing distutils-style scripts
    # # ----------------------------------
    #
    # # TODO Since zc.buildout 4.11 we can no longer detect distutils scripts in
    # # development eggs.  And now not in normal installs either.  Might be fixable,
    # # but for now it is causing too much trouble.
    #
    # # Most python libraries use the console_scripts entry point nowadays.  But
    # # several still have a ``scripts=['bin/something']`` in their setup() call.
    # # Buildout also installs those:
    #
    # #     >>> distdir = tmpdir('distutilsscriptdir')
    # #     >>> distbin = tmpdir('distutilsscriptbin')
    # #     >>> ws = zc.buildout.easy_install.install(
    # #     ...     ['other'], distdir,
    # #     ...     links=[link_server], index=link_server+'index/')
    # #     >>> scripts = zc.buildout.easy_install.scripts(
    # #     ...     ['other'], ws, sys.executable, distbin)
    # #     >>> ls(distbin)
    # #     -  distutilsscript
    #
    # # Like for console_scripts, the output is a list of the scripts
    # # generated. Likewise, on windows two files, an ``.exe`` and a script with
    # # ``-script.py`` appended, are generated:
    #
    # #     >>> import os, sys
    # #     >>> if sys.platform == 'win32':
    # #     ...     scripts == [os.path.join(distbin, 'distutilsscript.exe'),
    # #     ...                 os.path.join(distbin, 'distutilsscript-script.py')]
    # #     ... else:
    # #     ...     scripts == [os.path.join(distbin, 'distutilsscript')]
    # #     True
    #
    # # It also works for zipped eggs:
    #
    # #     >>> distdir2 = tmpdir('distutilsscriptdir2')
    # #     >>> distbin2 = tmpdir('distutilsscriptbin2')
    # #     >>> ws = zc.buildout.easy_install.install(
    # #     ...     ['du_zipped'], distdir2,
    # #     ...     links=[link_server], index=link_server+'index/')
    # #     >>> scripts = zc.buildout.easy_install.scripts(
    # #     ...     ['du_zipped'], ws, sys.executable, distbin2)
    # #     >>> ls(distbin2)
    # #     -  distutilsscript
    #
    # # Distutils copies the script files verbatim, apart from a line at the top that
    # # looks like ``#!/usr/bin/python``, which gets replaced by the actual python
    # # interpreter. Buildout does the same, but additionally also adds the sys.path
    # # like for the console_scripts.
    #
    # #     >>> cat(distbin, 'distutilsscript')
    # #     #!/usr/local/bin/python2.7
    # #     # -*- coding: utf-8 -*-
    # #     """Module docstring."""
    # #     <BLANKLINE>
    # #     <BLANKLINE>
    # #     import sys
    # #     sys.path[0:0] = [
    # #       '/distutilsscriptdir/other-1.0-pyN.N.egg',
    # #       ]
    # #     <BLANKLINE>
    # #     <BLANKLINE>
    # #     import os
    # #     import sys; sys.stdout.write("distutils!\n")
    #
    # # Note that there are several items that need to come first in such a script
    # # *before* buildout's ``sys.path`` statements: a source encoding hint, a module
    # # docstring and ``__future__`` imports. Buildout retains them in their proper
    # # place by looking at the first non-future import and placing its ``sys.path``
    # # statement before that.
    #
    # # Due to the nature of distutils scripts, buildout cannot pass arguments as
    # # there's no specific method to pass them to.
    #
    # # In some cases, a python 3 ``__pycache__`` directory can end up in an internal
    # # ``EGG-INFO`` metadata directory, next to the script information we're looking
    # # for. Buildout doesn't crash on that:
    #
    # #     >>> eggname = [name for name in os.listdir(distdir2)
    # #     ...            if name.endswith('egg')][0]
    # #     >>> scripts_metadata_dir = os.path.join(
    # #     ...     distdir2, eggname, 'EGG-INFO', 'scripts')
    # #     >>> os.mkdir(os.path.join(scripts_metadata_dir, '__dummy__'))
    # #     >>> scripts = zc.buildout.easy_install.scripts(
    # #     ...     ['du_zipped'], ws, sys.executable, distbin2)
    # #     >>> ls(distbin2)
    # #     -  distutilsscript
    #
    # # Installing develop eggs sadly means that setuptools doesn't record distutils
    # # scripts in the metadata. We try to detect such scripts anyhow:
    #
    # #     >>> dev_distutils_dir = tmpdir('dev_distutils_dir')
    # #     >>> dev_distutils_dest = tmpdir('dev_distutils_dest')
    # #     >>> dev_eggs_dir = os.path.join(dev_distutils_dest, 'develop-eggs')
    # #     >>> bin_dir = os.path.join(dev_distutils_dest, 'bin')
    # #     >>> os.mkdir(dev_eggs_dir)
    # #     >>> os.mkdir(bin_dir)
    # #     >>> write(dev_distutils_dir, 'distutilsscript2',
    # #     ...     '#!/usr/bin/python\n'
    # #     ...     '# -*- coding: utf-8 -*-\n'
    # #     ...     '"""Module docstring."""\n'
    # #     ...     'import os\n'
    # #     ...     'import sys; sys.stdout.write("distutils!\\n")\n'
    # #     ...     )
    # #     >>> write(dev_distutils_dir, 'setup.py',
    # #     ... '''
    # #     ... from setuptools import setup
    # #     ... setup(name="foo2",
    # #     ...       scripts=['distutilsscript2'])
    # #     ... ''')
    # #     >>> zc.buildout.easy_install.develop(
    # #     ...   dev_distutils_dir, dev_eggs_dir)
    # #     '/dev_distutils_dest/develop-eggs/foo2.egg-link'
    # #     >>> ws = zc.buildout.easy_install.working_set(
    # #     ...     ['foo2'], sys.executable, [dev_eggs_dir])
    # #     >>> scripts = zc.buildout.easy_install.scripts(
    # #     ...     ['foo2'], ws, sys.executable, dest=bin_dir)
    # #     >>> from zc.buildout.utils import IS_SETUPTOOLS_80_PLUS
    # #     >>> if IS_SETUPTOOLS_80_PLUS:
    # #     ...     # distutils scripts are no longer detected here
    # #     ...     True
    # #     ... elif sys.platform == 'win32':
    # #     ...     scripts == [os.path.join(dev_distutils_dest, 'bin', 'distutilsscript2.exe'),
    # #     ...                 os.path.join(dev_distutils_dest, 'bin', 'distutilsscript2-script.py')]
    # #     ... else:
    # #     ...     scripts == [os.path.join(dev_distutils_dest, 'bin', 'distutilsscript2')]
    # #     True
    #
    #


def test_easy_install_build_options_build(easy_install_env):
    link_server = easy_install_env['link_server']
    ls = easy_install_env['ls']
    mkdir = easy_install_env['mkdir']
    os = easy_install_env['os']
    sample_buildout = easy_install_env['sample_buildout']
    tmpdir = easy_install_env['tmpdir']
    write = easy_install_env['write']
    dest = tmpdir('sample-install')
    zc.buildout.easy_install.install(
        ['demo'], dest, links=[link_server], index=link_server+'index/',
        versions={'demo': '0.2', 'demoneeded': '1.0'})
    zc.buildout.easy_install.install(
        ['demo'], dest, links=[link_server], index=link_server+'index/')

    # Handling custom build options for extensions provided in source distributions
    # -----------------------------------------------------------------------------
    #
    # Sometimes, we need to control how extension modules are built.  The
    # build function provides this level of control.  It takes a single
    # package specification, downloads a source distribution, and builds it
    # with specified custom build options.
    #
    # The build function takes 3 positional arguments:
    #
    # spec
    #    A package specification for a source distribution
    #
    # dest
    #    A destination directory
    #
    # build_ext
    #    A dictionary of options to be passed to the distutils build_ext
    #    command when building extensions.
    #
    # It supports a number of optional keyword arguments:
    #
    # links
    #    a sequence of URLs, file names, or directories to look for
    #    links to distributions,
    #
    # index
    #    The URL of an index server, or almost any other valid URL. :)
    #
    #    If not specified, the Python Package Index,
    #    https://pypi.org/simple/, is used.  You can specify an
    #    alternate index with this option.  If you use the links option and
    #    if the links point to the needed distributions, then the index can
    #    be anything and will be largely ignored.  In the examples, here,
    #    we'll just point to an empty directory on our link server.  This
    #    will make our examples run a little bit faster.
    #
    # path
    #    A list of additional directories to search for locally-installed
    #    distributions.
    #
    # newest
    #    A boolean value indicating whether to search for new distributions
    #    when already-installed distributions meet the requirement.  When
    #    this is true, the default, and when the destination directory is
    #    not None, then the install function will search for the newest
    #    distributions that satisfy the requirements.
    #
    # versions
    #    A dictionary mapping project names to version numbers to be used
    #    when selecting distributions.  This can be used to specify a set of
    #    distribution versions independent of other requirements.
    #
    #
    # Our link server included a source distribution that includes a simple
    # extension, extdemo.c::
    #
    #   #include <Python.h>
    #   #include <extdemo.h>
    #
    #   static PyMethodDef methods[] = {};
    #
    #   PyMODINIT_FUNC
    #   initextdemo(void)
    #   {
    #       PyObject *m;
    #       m = Py_InitModule3("extdemo", methods, "");
    #   #ifdef TWO
    #       PyModule_AddObject(m, "val", PyInt_FromLong(2));
    #   #else
    #       PyModule_AddObject(m, "val", PyInt_FromLong(EXTDEMO));
    #   #endif
    #   }
    #
    # The extension depends on a system-dependent include file, extdemo.h,
    # that defines a constant, EXTDEMO, that is exposed by the extension.
    #
    # We'll add an include directory to our sample buildout and add the
    # needed include file to it:
    mkdir('include')
    write('include', 'extdemo.h',
    """
    #define EXTDEMO 42
    """)
    # Now, we can use the build function to create an egg from the source
    # distribution:
    _val = (zc.buildout.easy_install.build(
  'extdemo', dest,
  {'include_dirs': os.path.join(sample_buildout, 'include')},
  links=[link_server], index=link_server+'index/'))
    assert_output(str(_val), "['/sample-install/extdemo-1.4-py2.4-unix-i686.egg']", N)
    # The function returns the list of eggs
    #
    # Now if we look in our destination directory, we see we have an extdemo egg:
    assert_output(capture_print(ls, dest), """
d  demo-0.2-py2.4.egg
d  demo-0.3-py2.4.egg
d  demoneeded-1.0-py2.4.egg
d  demoneeded-1.1-py2.4.egg
d  extdemo-1.4-py2.4-unix-i686.egg
""", N)


def test_easy_install_build_options_update(easy_install_env):
    get = easy_install_env['get']
    link_server = easy_install_env['link_server']
    ls = easy_install_env['ls']
    mkdir = easy_install_env['mkdir']
    os = easy_install_env['os']
    sample_buildout = easy_install_env['sample_buildout']
    tmpdir = easy_install_env['tmpdir']
    update_extdemo = easy_install_env['update_extdemo']
    write = easy_install_env['write']
    dest = tmpdir('sample-install')
    zc.buildout.easy_install.install(
        ['demo'], dest, links=[link_server], index=link_server+'index/',
        versions={'demo': '0.2', 'demoneeded': '1.0'})
    zc.buildout.easy_install.install(
        ['demo'], dest, links=[link_server], index=link_server+'index/')
    # We'll add an include directory to our sample buildout and add the
    # needed include file to it:
    mkdir('include')
    write('include', 'extdemo.h',
    """
    #define EXTDEMO 42
    """)
    # Now, we can use the build function to create an egg from the source
    # distribution:
    _val = (zc.buildout.easy_install.build(
  'extdemo', dest,
  {'include_dirs': os.path.join(sample_buildout, 'include')},
  links=[link_server], index=link_server+'index/'))
    assert_output(str(_val), "['/sample-install/extdemo-1.4-py2.4-unix-i686.egg']", N)
    # The function returns the list of eggs
    #
    # Now if we look in our destination directory, we see we have an extdemo egg:
    assert_output(capture_print(ls, dest), """
d  demo-0.2-py2.4.egg
d  demo-0.3-py2.4.egg
d  demoneeded-1.0-py2.4.egg
d  demoneeded-1.1-py2.4.egg
d  extdemo-1.4-py2.4-unix-i686.egg
""", N)

    # Let's update our link server with a new version of extdemo:
    update_extdemo()
    assert_output(str(get(link_server)), """
<html><body>
<a href="bigdemo-0.1-py3-none-any.whl">bigdemo-0.1-py3-none-any.whl</a><br>
<a href="demo-0.1-py3-none-any.whl">demo-0.1-py3-none-any.whl</a><br>
<a href="demo-0.2-py3-none-any.whl">demo-0.2-py3-none-any.whl</a><br>
<a href="demo-0.3-py3-none-any.whl">demo-0.3-py3-none-any.whl</a><br>
<a href="demo-0.4rc1-py3-none-any.whl">demo-0.4rc1-py3-none-any.whl</a><br>
<a href="demoneeded-1.0.tar.gz">demoneeded-1.0.tar.gz</a><br>
<a href="demoneeded-1.1.tar.gz">demoneeded-1.1.tar.gz</a><br>
<a href="demoneeded-1.2rc1.tar.gz">demoneeded-1.2rc1.tar.gz</a><br>
<a href="du_zipped-1.0-pyN.N.egg">du_zipped-1.0-pyN.N.egg</a><br>
<a href="extdemo-1.4.tar.gz">extdemo-1.4.tar.gz</a><br>
<a href="extdemo-1.5.tar.gz">extdemo-1.5.tar.gz</a><br>
<a href="index/">index/</a><br>
<a href="mixedcase-0.5.tar.gz">mixedcase-0.5.tar.gz</a><br>
<a href="other-1.0-py3-none-any.whl">other-1.0-py3-none-any.whl</a><br>
</body></html>
""", N)
    # The easy_install caches information about servers to reduce network
    # access. To see the update, we have to call the clear_index_cache
    # function to clear the index cache:
    zc.buildout.easy_install.clear_index_cache()
    # If we run build with newest set to False, we won't get an update:
    _val = (zc.buildout.easy_install.build(
  'extdemo', dest,
  {'include_dirs': os.path.join(sample_buildout, 'include')},
  links=[link_server], index=link_server+'index/',
  newest=False))
    assert_output(str(_val), "['/sample-install/extdemo-1.4-py2.4-linux-i686.egg']", N)
    assert_output(capture_print(ls, dest), """
d  demo-0.2-py2.4.egg
d  demo-0.3-py2.4.egg
d  demoneeded-1.0-py2.4.egg
d  demoneeded-1.1-py2.4.egg
d  extdemo-1.4-py2.4-unix-i686.egg
""", N)
    # But if we run it with the default True setting for newest, then we'll
    # get an updated egg:
    _val = (zc.buildout.easy_install.build(
  'extdemo', dest,
  {'include_dirs': os.path.join(sample_buildout, 'include')},
  links=[link_server], index=link_server+'index/'))
    assert_output(str(_val), "['/sample-install/extdemo-1.5-py2.4-unix-i686.egg']", N)
    assert_output(capture_print(ls, dest), """
d  demo-0.2-py2.4.egg
d  demo-0.3-py2.4.egg
d  demoneeded-1.0-py2.4.egg
d  demoneeded-1.1-py2.4.egg
d  extdemo-1.4-py2.4-unix-i686.egg
d  extdemo-1.5-py2.4-unix-i686.egg
""", N)


def test_easy_install_build_options_versions(easy_install_env):
    link_server = easy_install_env['link_server']
    ls = easy_install_env['ls']
    mkdir = easy_install_env['mkdir']
    remove = easy_install_env['remove']
    sample_buildout = easy_install_env['sample_buildout']
    tmpdir = easy_install_env['tmpdir']
    update_extdemo = easy_install_env['update_extdemo']
    write = easy_install_env['write']
    dest = tmpdir('sample-install')
    mkdir('include')
    write('include', 'extdemo.h',
    """
    #define EXTDEMO 42
    """)
    update_extdemo()
    zc.buildout.easy_install.clear_index_cache()

    # The versions option also influences the versions used.  For example,
    # if we specify a version for extdemo, then that will be used, even
    # though it isn't the newest.  Let's clean out the destination directory
    # first:
    import os
    for name in os.listdir(dest):
        remove(dest, name)
    _val = (zc.buildout.easy_install.build(
  'extdemo', dest,
  {'include_dirs': os.path.join(sample_buildout, 'include')},
  links=[link_server], index=link_server+'index/',
  versions={'extdemo': '1.4'}))
    assert_output(str(_val), "['/sample-install/extdemo-1.4-py2.4-unix-i686.egg']", N)
    assert_output(capture_print(ls, dest), 'd  extdemo-1.4-py2.4-unix-i686.egg', N)


def test_easy_install_build_options_develop(easy_install_env):
    extdemo = easy_install_env['extdemo']
    link_server = easy_install_env['link_server']
    ls = easy_install_env['ls']
    mkdir = easy_install_env['mkdir']
    os = easy_install_env['os']
    sample_buildout = easy_install_env['sample_buildout']
    tmpdir = easy_install_env['tmpdir']
    write = easy_install_env['write']
    dest = tmpdir('sample-install')
    mkdir('include')
    write('include', 'extdemo.h',
    """
    #define EXTDEMO 42
    """)
    zc.buildout.easy_install.build(
  'extdemo', dest,
  {'include_dirs': os.path.join(sample_buildout, 'include')},
  links=[link_server], index=link_server+'index/')

    # Handling custom build options for extensions in develop eggs
    # ------------------------------------------------------------
    #
    # The develop function is similar to the build function, except that,
    # rather than building an egg from a source directory containing a
    # setup.py script.
    #
    # The develop function takes 2 positional arguments:
    #
    # setup
    #    The path to a setup script, typically named "setup.py", or a
    #    directory containing a setup.py script.
    #
    # dest
    #    The directory to install the egg link to
    #
    # It supports some optional keyword argument:
    #
    # build_ext
    #    A dictionary of options to be passed to the distutils build_ext
    #    command when building extensions.
    #
    # We have a local directory containing the extdemo source:
    contents = os.listdir(extdemo)
    _val = ('MANIFEST.in' in contents)
    assert repr(_val) == 'True' or str(_val) == 'True'
    _val = ('README' in contents)
    assert repr(_val) == 'True' or str(_val) == 'True'
    _val = ('extdemo.c' in contents)
    assert repr(_val) == 'True' or str(_val) == 'True'
    _val = ('setup.py' in contents)
    assert repr(_val) == 'True' or str(_val) == 'True'
    # Now, we can use the develop function to create a develop egg from the source
    # distribution:
    _val = (zc.buildout.easy_install.develop(
  extdemo, dest,
  {'include_dirs': os.path.join(sample_buildout, 'include')}))
    assert_output(str(_val), "/sample-install/extdemo.egg-link", N)
    # The name of the egg link created is returned.
    #
    # Now if we look in our destination directory, we see we have an extdemo
    # egg link:
    assert_output(capture_print(ls, dest), """
d  extdemo-1.4-py2.4-unix-i686.egg
-  extdemo.egg-link
""", N)
    # And that the source directory contains the compiled extension:
    contents = os.listdir(extdemo)
    _val = (bool([f for f in contents if f.endswith(('.so', '.pyd'))]))
    assert repr(_val) == 'True' or str(_val) == 'True'


def test_easy_install_download_cache(easy_install_env):
    get = easy_install_env['get']
    link_server = easy_install_env['link_server']
    ls = easy_install_env['ls']
    mkdir = easy_install_env['mkdir']
    os = easy_install_env['os']
    remove = easy_install_env['remove']
    sample_buildout = easy_install_env['sample_buildout']
    tmpdir = easy_install_env['tmpdir']
    update_extdemo = easy_install_env['update_extdemo']
    write = easy_install_env['write']
    mkdir('include')
    write('include', 'extdemo.h',
    """
    #define EXTDEMO 42
    """)
    update_extdemo()

    # Download cache
    # --------------
    #
    # Normally, when distributions are installed, if any processing is
    # needed, they are downloaded from the internet to a temporary directory
    # and then installed from there.  A download cache can be used to avoid
    # the download step.  This can be useful to reduce network access and to
    # create source distributions of an entire buildout.
    #
    # A download cache is specified by calling the download_cache
    # function.  The function always returns the previous setting. If no
    # argument is passed, then the setting is unchanged.  If an argument is
    # passed, the download cache is set to the given path, which must point
    # to an existing directory.  Passing None clears the cache setting.
    #
    # To see this work, we'll create a directory and set it as the cache
    # directory:
    cache = tmpdir('cache')
    zc.buildout.easy_install.download_cache(cache)
    # We create a destination directory:
    dest = tmpdir('sample-install')
    # We'd like to see what is being fetched from the server, so we'll
    # enable server logging:
    _ = get(link_server+'enable_server_logging')
    # TODO assert: 'GET 200 /enable_server_logging'
    # Now, if we install demo, and extdemo:
    ws = zc.buildout.easy_install.install(
        ['demo==0.2'], dest,
        links=[link_server], index=link_server+'index/')
    # TODO assert: 'GET 200 /\nGET 404 /index/demo/\nGET 200 /index/\nGET 200 /demo'
    _result = []
    def _build_extdemo():
        _result.append(zc.buildout.easy_install.build(
            'extdemo', dest,
            {'include_dirs': os.path.join(sample_buildout, 'include')},
            links=[link_server], index=link_server+'index/'))
    assert_output(capture_print(_build_extdemo), """
GET 404 /index/extdemo/
GET 200 /extdemo-1.5.tar.gz
""", N)
    assert_output(str(_result[0]), "['/sample-install/extdemo-1.5-py2.4-linux-i686.egg']", N)
    # Not only will we get eggs in our destination directory:
    assert_output(capture_print(ls, dest), """
d  demo-0.2-py2.4.egg
d  demoneeded-1.1-py2.4.egg
d  extdemo-1.5-py2.4-linux-i686.egg
""", N)
    # But we'll get distributions in the cache directory:
    assert_output(capture_print(ls, cache), """
-  demo-0.2-py3-none-any.whl
-  demoneeded-1.1.tar.gz
-  extdemo-1.5.tar.gz
""", N)
    # The cache directory contains uninstalled distributions, such as zipped
    # eggs or source distributions.
    #
    # Let's recreate our destination directory and clear the index cache:
    remove(dest)
    dest = tmpdir('sample-install')
    zc.buildout.easy_install.clear_index_cache()
    # Now when we install the distributions:
    ws = zc.buildout.easy_install.install(
        ['demo==0.2'], dest,
        links=[link_server], index=link_server+'index/')
    # TODO assert: 'GET 200 /\nGET 404 /index/demo/\nGET 200 /index/\nGET 404 /inde'
    _result2 = []
    def _build_extdemo2():
        _result2.append(zc.buildout.easy_install.build(
            'extdemo', dest,
            {'include_dirs': os.path.join(sample_buildout, 'include')},
            links=[link_server], index=link_server+'index/'))
    assert_output(capture_print(_build_extdemo2), """
GET 404 /index/extdemo/
""", N)
    assert_output(str(_result2[0]), "['/sample-install/extdemo-1.5-py2.4-linux-i686.egg']", N)
    assert_output(capture_print(ls, dest), """
d  demo-0.2-py2.4.egg
d  demoneeded-1.1-py2.4.egg
d  extdemo-1.5-py2.4-linux-i686.egg
""", N)
    # Note that we didn't download the distributions from the link server.
    #
    # If we remove the restriction on demo, we'll download a newer version
    # from the link server:
    ws = zc.buildout.easy_install.install(
        ['demo'], dest,
        links=[link_server], index=link_server+'index/')
    # TODO assert: 'GET 200 /demo-0.3-py3-none-any.whl'
    # Normally, the download cache is the preferred source of downloads, but
    # not the only one.
    #
    # Installing solely from a download cache
    # ---------------------------------------
    #
    # A download cache can be used as the basis of application source
    # releases.  In an application source release, we want to distribute an
    # application that can be built without making any network accesses.  In
    # this case, we distribute a download cache and tell the easy_install
    # module to install from the download cache only, without making network
    # accesses.  The install_from_cache function can be used to signal that
    # packages should be installed only from the download cache.  The
    # function always returns the previous setting.  Calling it with no
    # arguments returns the current setting without changing it:
    _val = (zc.buildout.easy_install.install_from_cache())
    assert repr(_val) == 'False' or str(_val) == 'False'
    # Calling it with a boolean value changes the setting and returns the
    # previous setting:
    _val = (zc.buildout.easy_install.install_from_cache(True))
    assert repr(_val) == 'False' or str(_val) == 'False'
    # Let's remove demo-0.3-py2.4.egg from the cache, clear the index cache,
    # recreate the destination directory, and reinstall demo:
    for  f in os.listdir(cache):
        if f.startswith('demo-0.3-'):
            remove(cache, f)
    zc.buildout.easy_install.clear_index_cache()
    remove(dest)
    dest = tmpdir('sample-install')
    ws = zc.buildout.easy_install.install(
        ['demo'], dest,
        links=[link_server], index=link_server+'index/')
    assert_output(capture_print(ls, dest), """
d  demo-0.2-py2.4.egg
d  demoneeded-1.1-py2.4.egg
""", N)
    # This time, we didn't download from or even query the link server.
    #
    # .. Disable the download cache:
    _val = (zc.buildout.easy_install.download_cache(None))
    assert_output(str(_val), "/cache", N)
    _val = (zc.buildout.easy_install.install_from_cache(False))
    assert repr(_val) == 'True' or str(_val) == 'True'
    # Environment markers
    # -------------------
    #
    #     Specifications can include PEP 496 environment markers.
    _ = get(link_server + 'disable_server_logging')
    spec = ["demo ==0.1; python_version < '3.10'",
    "demo == 0.2; python_version >= '3.10'"]
    ws = zc.buildout.easy_install.install(
    spec, dest, links=[link_server], index=link_server+'index/')
    demo_version = None
    for egg in ws:
        if egg.project_name == 'demo':
            demo_version = egg.version
    _val = (demo_version is not None)
    assert repr(_val) == 'True' or str(_val) == 'True'
    _val = (demo_version if (sys.version_info < (3, 10)) else '0.1')
    assert repr(_val) == "'0.1'" or str(_val) == "'0.1'"
    _val = (demo_version if (sys.version_info >= (3, 10)) else '0.2')
    assert repr(_val) == "'0.2'" or str(_val) == "'0.2'"
    # Conflicts properly with version spec.
    try:
        ws = zc.buildout.easy_install.install(
        spec, dest, links=[link_server], index=link_server+'index/',
        versions = {'demo': '0.3'})
        assert False, "Expected zc.buildout.easy_install.IncompatibleConstraintError not raised"
    except Exception as _exc:  # noqa: BLE001 - the class
        # and message are pinned by the assertion below
        assert_output(str(_exc), "The requirement ('demo==0...", N)


def test_downloadcache(easy_install_env):
    buildout = easy_install_env['buildout']
    cd = easy_install_env['cd']
    get = easy_install_env['get']
    link_server = easy_install_env['link_server']
    ls = easy_install_env['ls']
    remove = easy_install_env['remove']
    sample_buildout = easy_install_env['sample_buildout']
    start_server = easy_install_env['start_server']
    system = easy_install_env['system']
    tmpdir = easy_install_env['tmpdir']
    write = easy_install_env['write']

    # Using a download cache
    # ======================
    #
    # Normally, when distributions are installed, if any processing is
    # needed, they are downloaded from the internet to a temporary directory
    # and then installed from there.  A download cache can be used to avoid
    # the download step.  This can be useful to reduce network access and to
    # create source distributions of an entire buildout.
    #
    # The buildout download-cache option can be used to specify a directory
    # to be used as a download cache.
    #
    # In this example, we'll create a directory to hold the cache:
    cache = tmpdir('cache')
    # And set up a buildout that downloads some eggs:
    write('buildout.cfg',
    '''
    [buildout]
    parts = eggs
    download-cache = {cache}
    find-links = {link_server}
    
    [eggs]
    recipe = zc.recipe.egg
    eggs = demo ==0.2
    '''.format_map(locals()))
    # We specified a link server that has some distributions available for
    # download:
    assert_output(str(get(link_server)), """
<html><body>
<a href="bigdemo-0.1-py3-none-any.whl">bigdemo-0.1-py3-none-any.whl</a><br>
<a href="demo-0.1-py3-none-any.whl">demo-0.1-py3-none-any.whl</a><br>
<a href="demo-0.2-py3-none-any.whl">demo-0.2-py3-none-any.whl</a><br>
<a href="demo-0.3-py3-none-any.whl">demo-0.3-py3-none-any.whl</a><br>
<a href="demo-0.4rc1-py3-none-any.whl">demo-0.4rc1-py3-none-any.whl</a><br>
<a href="demoneeded-1.0.tar.gz">demoneeded-1.0.tar.gz</a><br>
<a href="demoneeded-1.1.tar.gz">demoneeded-1.1.tar.gz</a><br>
<a href="demoneeded-1.2rc1.tar.gz">demoneeded-1.2rc1.tar.gz</a><br>
<a href="du_zipped-1.0-pyN.N.egg">du_zipped-1.0-pyN.N.egg</a><br>
<a href="extdemo-1.4.tar.gz">extdemo-1.4.tar.gz</a><br>
<a href="index/">index/</a><br>
<a href="mixedcase-0.5.tar.gz">mixedcase-0.5.tar.gz</a><br>
<a href="other-1.0-py3-none-any.whl">other-1.0-py3-none-any.whl</a><br>
</body></html>
""", N)
    # We'll enable logging on the link server so we can see what's going on:
    _ = get(link_server+'enable_server_logging')
    # TODO assert: 'GET 200 /enable_server_logging'
    # We also specified a download cache.
    #
    # If we run the buildout, we'll see the eggs installed from the link
    # server as usual:
    assert_output(system(buildout), """
Installing eggs.
Getting distribution for 'demo==0.2'.
Got demo 0.2.
Getting distribution for 'demoneeded'.
Got demoneeded 1.1.
Generated script '/sample-buildout/bin/demo'.
""", N)
    # We'll also get the download cache populated.  The buildout doesn't put
    # files in the cache directly.  It creates an intermediate directory,
    # dist:
    assert_output(capture_print(ls, cache), 'd  dist', N)
    assert_output(capture_print(ls, cache, 'dist'), """
-  demo-0.2-py3-none-any.whl
-  demoneeded-1.1.tar.gz
""", N)
    # If we remove the installed eggs from eggs directory and re-run the buildout:
    import os
    for f in os.listdir(os.path.join('eggs', 'v5')):
        if f.startswith('demo'):
            remove('eggs', 'v5', f)
    assert_output(system(buildout), """
Updating eggs.
Getting distribution for 'demo==0.2'.
Got demo 0.2.
Getting distribution for 'demoneeded'.
Got demoneeded 1.1.
""", N)
    # We see that the distributions aren't downloaded, because they're
    # downloaded from the cache.
    #
    # Installing solely from a download cache
    # ---------------------------------------
    #
    # A download cache can be used as the basis of application source
    # releases.  In an application source release, we want to distribute an
    # application that can be built without making any network accesses.  In
    # this case, we distribute a buildout with download cache and tell the
    # buildout to install from the download cache only, without making
    # network accesses.  The buildout install-from-cache option can be used
    # to signal that packages should be installed only from the download
    # cache.
    #
    # Let's remove our installed eggs and run the buildout with the
    # install-from-cache option set to true:
    for f in os.listdir(os.path.join('eggs', 'v5')):
        if f.startswith('demo'):
            remove('eggs', 'v5', f)
    write('buildout.cfg',
    '''
    [buildout]
    parts = eggs
    download-cache = {cache}
    install-from-cache = true
    find-links = {link_server}
    
    [eggs]
    recipe = zc.recipe.egg
    eggs = demo
    '''.format_map(locals()))
    assert_output(system(buildout), """
Uninstalling eggs.
Installing eggs.
Getting distribution for 'demo'.
Got demo 0.2.
Getting distribution for 'demoneeded'.
Got demoneeded 1.1.
Generated script '/sample-buildout/bin/demo'.
""", N)
    # Auto-creation of download cache directory
    # -----------------------------------------
    #
    # With zc.buildout version 2.2.2 or higher the cache directory is automatically
    # created::
    write('buildout.cfg',
    '''
    [buildout]
    parts =
    download-cache = {cache}/newdir
    '''.format_map(locals()))
    assert_output(system(buildout), """
Creating directory '/cache/newdir'.
Uninstalling eggs.
""", N)
    assert_output(capture_print(ls, cache), """
d  dist
d  newdir
""", N)
    # Using relative paths
    # --------------------
    #
    # You can use a relative path for ``download-cache`` (the same logic is applied to
    # ``eggs-directory`` and to ``extends-cache`` too) and in such case it is considered
    # relative to the location of the configuration file that sets its value.
    #
    # As an example, we create a ``base.cfg`` configuration in a different directory::
    basedir = tmpdir('basecfg')
    write(basedir, 'base.cfg',
    '''
    [buildout]
    download-cache = cache
    ''')
    # and a ``buildout.cfg`` that extends from there::
    write('buildout.cfg',
    '''
    [buildout]
    extends = {basedir}/base.cfg
    parts =
    '''.format_map(locals()))
    dummy = system(buildout)
    assert_output(capture_print(ls, basedir), """
-  base.cfg
d  cache
""", N)
    # Of course this cannot be used when the base configuration is not on the local
    # filesystem because it wouldn't make any sense having a remote cache::
    server_data = tmpdir('server_data')
    server_url = start_server(server_data)
    cd(sample_buildout)
    write(server_data, 'base.cfg', """\
    [buildout]
    download-cache = cache
    """)
    write('buildout.cfg',
    '''
    [buildout]
    extends = {server_url}/base.cfg
    parts =
    '''.format_map(locals()))
    assert_output(system(buildout), """
While:
  Initializing.
Error: Setting "download-cache" to a non absolute location ("cache") within a
remote configuration file...
""", N)
    # Though, you can create the ``download-cache`` within a nested directory, so that you can
    # group all your generated directories (like ``eggs-directory`` or ``extends-cache`` too)
    # within a single directory:
    test_nested = tmpdir('test_nested')
    cd(test_nested)
    write('buildout.cfg',
    '''
    [buildout]
    download-cache = ${buildout:directory}/var/cache
    eggs-directory = ${buildout:directory}/var/eggs
    parts-directory = ${buildout:directory}/var/parts
    develop-eggs-directory = ${buildout:directory}/var/develop-eggs
    ''')
    dummy = system(buildout)
    assert_output(capture_print(ls, test_nested), """
d  bin
-  buildout.cfg
d  var
""", N)
    assert_output(capture_print(ls, os.path.join(test_nested, 'var')), """
d  cache
d  develop-eggs
d  eggs
d  parts
""", N)


def test_dependencylinks_metadata_followed(easy_install_env):
    buildout = easy_install_env['buildout']
    get = easy_install_env['get']
    mkdir = easy_install_env['mkdir']
    sample_buildout = easy_install_env['sample_buildout']
    sample_eggs = easy_install_env['sample_eggs']
    start_server = easy_install_env['start_server']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # Dependency links
    # ----------------
    #
    # By default buildout will obey the setuptools dependency_links metadata
    # when it looks for dependencies. This behavior can be controlled with
    # the use-dependency-links buildout option.
    #
    #   [buildout]
    #   ...
    #   use-dependency-links = false
    #
    # The option defaults to true. If you set it to false, then dependency
    # links are only looked for in the locations specified by find-links.
    #
    # Let's see this feature in action.  To begin, let's create a new egg
    # repository. This repository uses the same sample eggs as the normal
    # testing repository.
    link_server2 = start_server(sample_eggs)
    # Turn on logging on this server so that we can see when eggs are pulled
    # from it.
    _ = get(link_server2 + 'enable_server_logging')
    # TODO assert: 'GET 200 /enable_server_logging'
    # Let's create a develop egg in our buildout that specifies
    # dependency_links which point to the new server.
    mkdir(sample_buildout, 'depdemo')
    write(sample_buildout, 'depdemo', 'dependencydemo.py',
          'import eggrecipedemoneeded')
    write(sample_buildout, 'depdemo', 'setup.py',
    f'''from setuptools import setup; setup(
        name='depdemo', py_modules=['dependencydemo'],
        install_requires = 'demoneeded',
        dependency_links = ['{link_server2}'],
        zip_safe=True, version='1')
    ''')
    # Now let's configure the buildout to use the develop egg.
    write(sample_buildout, 'buildout.cfg',
    '''
    [buildout]
    develop = depdemo
    parts = eggs
    
    [eggs]
    recipe = zc.recipe.egg:eggs
    eggs = depdemo
    ''')
    # Now we can run the buildout.
    assert_output(system(buildout), """
Develop: '/sample-buildout/depdemo'
Installing eggs.
Getting distribution for 'demoneeded'.
Got demoneeded 1.1...
""", N)
    # Notice that the egg was retrieved from the logging server.
    # The output may have extra lines like this, at least on setuptools 63, which we ignore:
    #
    #     Not found: /demoneeded/
    #     Not found: /.VolumeIcon.icns
    #


def test_dependencylinks_fallback(easy_install_env):
    buildout = easy_install_env['buildout']
    get = easy_install_env['get']
    link_server = easy_install_env['link_server']
    mkdir = easy_install_env['mkdir']
    remove = easy_install_env['remove']
    sample_buildout = easy_install_env['sample_buildout']
    sample_eggs = easy_install_env['sample_eggs']
    start_server = easy_install_env['start_server']
    system = easy_install_env['system']
    write = easy_install_env['write']
    # Let's see this feature in action.  To begin, let's create a new egg
    # repository. This repository uses the same sample eggs as the normal
    # testing repository.
    link_server2 = start_server(sample_eggs)
    # Turn on logging on this server so that we can see when eggs are pulled
    # from it.
    _ = get(link_server2 + 'enable_server_logging')
    # TODO assert: 'GET 200 /enable_server_logging'
    # Let's create a develop egg in our buildout that specifies
    # dependency_links which point to the new server.
    mkdir(sample_buildout, 'depdemo')
    write(sample_buildout, 'depdemo', 'dependencydemo.py',
          'import eggrecipedemoneeded')
    write(sample_buildout, 'depdemo', 'setup.py',
    f'''from setuptools import setup; setup(
        name='depdemo', py_modules=['dependencydemo'],
        install_requires = 'demoneeded',
        dependency_links = ['{link_server2}'],
        zip_safe=True, version='1')
    ''')
    # Now let's configure the buildout to use the develop egg.
    write(sample_buildout, 'buildout.cfg',
    '''
    [buildout]
    develop = depdemo
    parts = eggs
    
    [eggs]
    recipe = zc.recipe.egg:eggs
    eggs = depdemo
    ''')
    # Now we can run the buildout.
    assert_output(system(buildout), """
Develop: '/sample-buildout/depdemo'
Installing eggs.
Getting distribution for 'demoneeded'.
Got demoneeded 1.1...
""", N)
    # Notice that the egg was retrieved from the logging server.
    # The output may have extra lines like this, at least on setuptools 63, which we ignore:
    #
    #     Not found: /demoneeded/
    #     Not found: /.VolumeIcon.icns
    #

    # Now let's change the egg so that it doesn't specify dependency links.
    write(sample_buildout, 'depdemo', 'setup.py',
    '''from setuptools import setup; setup(
        name='depdemo', py_modules=['dependencydemo'],
        install_requires = 'demoneeded',
        zip_safe=True, version='1')
    ''')
    # Now we'll remove the existing dependency egg, and rerunning the
    # buildout to see where the egg comes from this time.
    from glob import glob
    from os.path import join
    def remove_demoneeded_egg():
        for egg in glob(join(sample_buildout, 'eggs', 'v5', 'demoneeded*.egg')):
            remove(sample_buildout, 'eggs', egg)
    remove_demoneeded_egg()
    assert_output(system(buildout), """
Develop: '/sample-buildout/depdemo'
Updating eggs.
...
While:
  Updating eggs.
  Getting distribution for 'demoneeded'.
Error: Couldn't find a distribution for 'demoneeded'.
""", N)
    # Now it can't find the dependency since neither the buildout
    # configuration nor setup specifies where to look.
    #
    # Let's change things so that the buildout configuration specifies where
    # to look for eggs.
    write(sample_buildout, 'buildout.cfg',
    f'''
    [buildout]
    develop = depdemo
    parts = eggs
    find-links = {link_server}
    
    [eggs]
    recipe = zc.recipe.egg:eggs
    eggs = depdemo
    ''')
    assert_output(system(buildout), """
Develop: '/sample-buildout/depdemo'
Installing eggs.
Getting distribution for 'demoneeded'.
Got demoneeded 1.1.
""", N)
    # This time the dependency egg was found on the server without logging
    # configured.
    #


def test_dependencylinks_option(easy_install_env):
    buildout = easy_install_env['buildout']
    get = easy_install_env['get']
    link_server = easy_install_env['link_server']
    mkdir = easy_install_env['mkdir']
    remove = easy_install_env['remove']
    sample_buildout = easy_install_env['sample_buildout']
    sample_eggs = easy_install_env['sample_eggs']
    start_server = easy_install_env['start_server']
    system = easy_install_env['system']
    write = easy_install_env['write']
    link_server2 = start_server(sample_eggs)
    _ = get(link_server2 + 'enable_server_logging')
    mkdir(sample_buildout, 'depdemo')
    write(sample_buildout, 'depdemo', 'dependencydemo.py',
          'import eggrecipedemoneeded')
    write(sample_buildout, 'depdemo', 'setup.py',
    '''from setuptools import setup; setup(
        name='depdemo', py_modules=['dependencydemo'],
        install_requires = 'demoneeded',
        zip_safe=True, version='1')
    ''')
    write(sample_buildout, 'buildout.cfg',
    f'''
    [buildout]
    develop = depdemo
    parts = eggs
    find-links = {link_server}
    
    [eggs]
    recipe = zc.recipe.egg:eggs
    eggs = depdemo
    ''')
    _ = system(buildout)
    from glob import glob
    from os.path import join
    def remove_demoneeded_egg():
        for egg in glob(join(sample_buildout, 'eggs', 'v5', 'demoneeded*.egg')):
            remove(sample_buildout, 'eggs', egg)

    # Now let's change things once again so that both buildout and setup
    # specify different places to look for the dependency egg.
    write(sample_buildout, 'depdemo', 'setup.py',
    f'''from setuptools import setup; setup(
        name='depdemo', py_modules=['dependencydemo'],
        install_requires = 'demoneeded',
        dependency_links = ['{link_server2}'],
        zip_safe=True, version='1')
    ''')
    remove_demoneeded_egg()
    assert_output(system(buildout), """
Develop: '/sample-buildout/depdemo'
Updating eggs.
Getting distribution for 'demoneeded'.
Got demoneeded 1.1...
""", N)
    # So when both setuptools and buildout specify places to search for
    # eggs, the dependency_links takes precedence over find-links.
    #
    # There is a buildout option that you can specify to change this
    # behavior. It is the use-dependency-links option. This option defaults
    # to true. When you specify false for this option, buildout will ignore
    # dependency_links and only look for eggs using find-links.
    #
    # Here is an example of using this option to disable dependency_links.
    write(sample_buildout, 'buildout.cfg',
    f'''
    [buildout]
    develop = depdemo
    parts = eggs
    find-links = {link_server}
    use-dependency-links = false
    
    [eggs]
    recipe = zc.recipe.egg:eggs
    eggs = depdemo
    ''')
    remove_demoneeded_egg()
    assert_output(system(buildout), """
Develop: '/sample-buildout/depdemo'
Updating eggs.
Getting distribution for 'demoneeded'.
Got demoneeded 1.1.
""", N)
    # Notice that this time the egg isn't downloaded from the logging server.
    #
    # If we set the option to true, things return to the way they were
    # before. The dependency's are looked for first in the logging server.
    write(sample_buildout, 'buildout.cfg',
    f'''
    [buildout]
    develop = depdemo
    parts = eggs
    find-links = {link_server}
    use-dependency-links = true
    
    [eggs]
    recipe = zc.recipe.egg:eggs
    eggs = depdemo
    ''')
    remove_demoneeded_egg()
    assert_output(system(buildout), """
Develop: '/sample-buildout/depdemo'
Updating eggs.
Getting distribution for 'demoneeded'.
Got demoneeded 1.1...
""", N)


def test_allowhosts(easy_install_env):
    buildout = easy_install_env['buildout']
    mkdir = easy_install_env['mkdir']
    print_ = easy_install_env['print_']
    sample_buildout = easy_install_env['sample_buildout']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # Allow hosts
    # -----------
    #
    # On some environments the links visited by `zc.buildout` can be forbidden
    # by paranoiac firewalls. These URL might be on the chain of links
    # visited by `zc.buildout` whether they are defined in the `find-links` option
    # or by various eggs in their `url`, `download_url` and `dependency_links` metadata.
    #
    # It is even harder to track that package_index works like a spider and
    # might visit links and go to other location.
    #
    # The `allow-hosts` option provides a way to prevent this, and
    # works exactly like the one provided in `easy_install`
    # (see `easy_install allow-hosts option`_).
    #
    # You can provide a list of allowed host, together with wildcards::
    #
    #     [buildout]
    #     ...
    #
    #     allow-hosts =
    #         *.python.org
    #         example.com
    #
    # Let's create a develop egg in our buildout that specifies
    # `dependency_links` which points to a server in the outside world::
    mkdir(sample_buildout, 'allowdemo')
    write(sample_buildout, 'allowdemo', 'dependencydemo.py',
          'import eggrecipekss.core')
    write(sample_buildout, 'allowdemo', 'setup.py',
    '''from setuptools import setup; setup(
        name='allowdemo', py_modules=['dependencydemo'],
        install_requires = 'kss.core',
        dependency_links = ['http://dist.plone.org'],
        zip_safe=True, version='1')
    ''')
    # Now let's configure the buildout to use the develop egg,
    # together with some rules that disallow any web site but PyPI and
    # local files::
    write(sample_buildout, 'buildout.cfg',
    '''
    [buildout]
    develop = allowdemo
    parts = eggs
    allow-hosts =
        pypi.org
    
    [eggs]
    recipe = zc.recipe.egg:eggs
    eggs = allowdemo
    ''')
    # Now we can run the buildout and make sure all attempts to dist.plone.org fails::
    assert_output(system(buildout), """
Develop: '/sample-buildout/allowdemo'
Installing eggs...
...
While:
  Installing eggs.
  Getting distribution for 'kss.core'.
Error: Couldn't find a distribution for 'kss.core'.
""", N)
    # That's what we wanted : this will prevent any attempt to access
    # unwanted domains. For instance, some packages are listing in their
    # links `svn://` links. These can lead to error in some cases, and
    # can therefore be protected like this::
    #
    # XXX (showcase with a svn:// file)
    write(sample_buildout, 'buildout.cfg',
    '''
    [buildout]
    develop = allowdemo
    parts = eggs
    allow-hosts =
        ^(!svn://).*
    
    [eggs]
    recipe = zc.recipe.egg:eggs
    eggs = allowdemo
    ''')
    # Now we can run the buildout and make sure all attempts to dist.plone.org fails::
    assert_output(system(buildout), """
Develop: '/sample-buildout/allowdemo'
Installing eggs...
...
While:
  Installing eggs.
  Getting distribution for 'kss.core'.
Error: Couldn't find a distribution for 'kss.core'.
""", N)
    # Test for issues
    # ---------------
    #
    # Test for 1.0.5 breakage as in
    # https://bugs.launchpad.net/zc.buildout/+bug/239212::
    write(sample_buildout, 'buildout.cfg',
    '''
    [buildout]
    parts=python
    foo = ${python:interpreter}
    
    [python]
    recipe=zc.recipe.egg
    eggs=zc.buildout
    interpreter=python
    ''')
    def _step():
        print_('XX')
        print_(system(buildout), end='')
    assert_output(capture_print(_step), """
X...
Section `buildout` contains unused option(s): 'foo'.
This may be an indication for either a typo in the option's name or a bug in the used recipe.
Installing python...
Generated interpreter '/sample-buildout/bin/python'.
""", N)
    # The bug 239212 above would have got us an *AttributeError* on
    # *buildout._allow_hosts*.  This was fixed in this changeset:
    # http://svn.zope.org/zc.buildout/trunk/src/zc/buildout/buildout.py?rev=87309&r1=87277&r2=87309

def test_allow_unknown_extras(easy_install_env):
    buildout = easy_install_env['buildout']
    mkdir = easy_install_env['mkdir']
    sample_buildout = easy_install_env['sample_buildout']
    system = easy_install_env['system']
    write = easy_install_env['write']

    # ======================
    #  Allow Unknown Extras
    # ======================
    #
    # Sometimes we need to allow unknown extras.
    #
    # The ``allow-unknown-extras`` option lets us do that in a buildout
    # configuration, just as we can directly calling ``easy_install``
    # works exactly like the one provided in ``easy_install``.
    #
    # Let's create a develop egg that requires a bogus extra.
    mkdir(sample_buildout, 'allowdemo')
    write(sample_buildout, 'allowdemo', 'dependencydemo.py',
          'import eggrecipekss.core')
    write(sample_buildout, 'allowdemo', 'setup.py',
    '''from setuptools import setup; setup(
        name='allowdemo', py_modules=['dependencydemo'],
        zip_safe=True, version='1')
    ''')
    # Now let's configure the buildout to use the develop egg with a bogus extra.
    write(sample_buildout, 'buildout.cfg',
    '''
    [buildout]
    develop = allowdemo
    parts = eggs
    
    [eggs]
    recipe = zc.recipe.egg:eggs
    eggs = allowdemo[bad_extra]
    ''')
    # Now we can run the buildout and see that it fails:
    assert_output(system(buildout), """
Develop: '/sample-buildout/allowdemo'
Installing eggs...
...
While:
  Installing eggs.
Error: Couldn't find the required extra...
""", N)
    # If we flip the option on, the buildout succeeds
    write(sample_buildout, 'buildout.cfg',
    '''
    [buildout]
    develop = allowdemo
    parts = eggs
    allow-unknown-extras = true
    
    [eggs]
    recipe = zc.recipe.egg:eggs
    eggs = allowdemo[bad_extra]
    ''')
    # Now we can run the buildout and only get a warning::
    assert_output(system(buildout), """
Develop: '/sample-buildout/allowdemo'
Installing eggs...
allowdemo 1 does not provide the extra 'bad_extra'
""", N)

def test_download(easy_install_env):
    cat = easy_install_env['cat']
    get = easy_install_env['get']
    join = easy_install_env['join']
    ls = easy_install_env['ls']
    mkdir = easy_install_env['mkdir']
    print_ = easy_install_env['print_']
    remove = easy_install_env['remove']
    rmdir = easy_install_env['rmdir']
    sample_buildout = easy_install_env['sample_buildout']
    start_server = easy_install_env['start_server']
    tmpdir = easy_install_env['tmpdir']
    write = easy_install_env['write']

    # Using the download utility
    # ==========================
    #
    # The ``zc.buildout.download`` module provides a download utility that handles
    # the details of downloading files needed for a buildout run from the internet.
    # It downloads files to the local file system, using the download cache if
    # desired and optionally checking the downloaded files' MD5 checksum.
    #
    # We setup an HTTP server that provides a file we want to download:
    server_data = tmpdir('sample_files')
    write(server_data, 'foo.txt', 'This is a foo text.')
    server_url = start_server(server_data)
    # We also use a fresh directory for temporary files in order to make sure that
    # all temporary files have been cleaned up in the end:
    import tempfile
    old_tempdir = tempfile.tempdir
    tempfile.tempdir = tmpdir('tmp')
    # Downloading without using the cache
    # -----------------------------------
    #
    # If no download cache should be used, the download utility is instantiated
    # without any arguments:
    from zc.buildout.download import Download
    download = Download()
    assert_output(str(download.cache_dir), 'None', N)
    # Downloading a file is achieved by calling the utility with the URL as an
    # argument. A tuple is returned that consists of the path to the downloaded copy
    # of the file and a boolean value indicating whether this is a temporary file
    # meant to be cleaned up during the same buildout run:
    path, is_temp = download(server_url+'foo.txt')
    assert_output(str(path), '/.../buildout-...', N)
    assert_output(capture_print(cat, path), 'This is a foo text.', N)
    # As we aren't using the download cache and haven't specified a target path
    # either, the download has ended up in a temporary file:
    _val = (is_temp)
    assert repr(_val) == 'True' or str(_val) == 'True'
    import tempfile
    _val = (path.startswith(tempfile.gettempdir()))
    assert repr(_val) == 'True' or str(_val) == 'True'
    # We are responsible for cleaning up temporary files behind us:
    remove(path)
    # When trying to access a file that doesn't exist, we'll get an exception:
    try:
        download(server_url+'not-there') # doctest: +ELLIPSIS
    except Exception:  # noqa: BLE001 - fallback marker print;
        # the error type is not under test here
        print_('download error')
    else:
        print_('woops')
    # TODO assert: 'download error'
    # Downloading a local file doesn't produce a temporary file but simply returns
    # the local file itself:
    _val = (download(join(server_data, 'foo.txt')))
    assert_output(str(_val), "('/sample_files/foo.txt', False)", N)
    # We can also have the downloaded file's MD5 sum checked:
    from hashlib import md5
    path, is_temp = download(server_url+'foo.txt',
                             md5(b'This is a foo text.').hexdigest())
    _val = (is_temp)
    assert repr(_val) == 'True' or str(_val) == 'True'
    remove(path)
    try:
        download(server_url+'foo.txt',
                 md5(b'The wrong text.').hexdigest())
        assert False, "Expected ChecksumError not raised"
    except Exception as _exc:  # noqa: BLE001 - the class
        # and message are pinned by the assertion below
        assert_output(str(_exc), "MD5 checksum mismatch downloading 'http://localhost/foo.txt'", N)
    # The error message in the event of an MD5 checksum mismatch for a local file
    # reads somewhat differently:
    _val = (download(join(server_data, 'foo.txt'),
              md5(b'This is a foo text.').hexdigest()))
    assert_output(str(_val), "('/sample_files/foo.txt', False)", N)
    try:
        download(join(server_data, 'foo.txt'),
                 md5(b'The wrong text.').hexdigest())
        assert False, "Expected ChecksumError not raised"
    except Exception as _exc:  # noqa: BLE001 - the class
        # and message are pinned by the assertion below
        assert_output(str(_exc), "MD5 checksum mismatch for local resource at '/sample_files/foo.txt'.", N)
    # Finally, we can download the file to a specified place in the file system:
    target_dir = tmpdir('download-target')
    path, is_temp = download(server_url+'foo.txt',
                             path=join(target_dir, 'downloaded.txt'))
    assert_output(str(path), '/download-target/downloaded.txt', N)
    assert_output(capture_print(cat, path), 'This is a foo text.', N)
    _val = (is_temp)
    assert repr(_val) == 'False' or str(_val) == 'False'
    # Trying to download a file in offline mode will result in an error:
    download = Download(cache=None, offline=True)
    try:
        download(server_url+'foo.txt')
        assert False, "Expected UserError not raised"
    except Exception as _exc:  # noqa: BLE001 - the class
        # and message are pinned by the assertion below
        assert_output(str(_exc), "Couldn't download 'http://localhost/foo.txt' in offline mode.\n"
                      "Run buildout once in online mode with a cache directory\n"
                      "configured: 'extends-cache' for configuration files,\n"
                      "'download-cache' for other files; the download is then\n"
                      "reused from the cache while offline.", N)
    # As an exception to this rule, file system paths and URLs in the ``file``
    # scheme will still work:
    assert_output(capture_print(cat, download(join(server_data, 'foo.txt'))[0]), 'This is a foo text.', N)
    assert_output(capture_print(cat, download('file:' + join(server_data, 'foo.txt'))[0]), 'This is a foo text.', N)
    remove(path)
    # Downloading using the download cache
    # ------------------------------------
    #
    # In order to make use of the download cache, we need to configure the download
    # utility differently. To do this, we pass a directory path as the ``cache``
    # attribute upon instantiation:
    cache = tmpdir('download-cache')
    download = Download(cache=cache)
    assert_output(str(download.cache_dir), '/download-cache/', N)
    # Simple usage
    # ~~~~~~~~~~~~
    #
    # When using the cache, a file will be stored in the cache directory when it is
    # first downloaded. The file system path returned by the download utility points
    # to the cached copy:
    ls(cache)
    path, is_temp = download(server_url+'foo.txt')
    assert_output(str(path), '/download-cache/foo.txt', N)
    assert_output(capture_print(cat, path), 'This is a foo text.', N)
    _val = (is_temp)
    assert repr(_val) == 'False' or str(_val) == 'False'
    # Whenever the file is downloaded again, the cached copy is used. Let's change
    # the file on the server to see this:
    write(server_data, 'foo.txt', 'The wrong text.')
    path, is_temp = download(server_url+'foo.txt')
    assert_output(str(path), '/download-cache/foo.txt', N)
    assert_output(capture_print(cat, path), 'This is a foo text.', N)
    # If we specify an MD5 checksum for a file that is already in the cache, the
    # cached copy's checksum will be verified:
    try:
        download(server_url+'foo.txt', md5(b'The wrong text.').hexdigest())
        assert False, "Expected from 'http not raised"
    except Exception as _exc:  # noqa: BLE001 - the class
        # and message are pinned by the assertion below
        assert_output(str(_exc), "               from 'http://localhost/foo.txt' at '/download-cache/foo.txt'", N)
    # Trying to access another file at a different URL which has the same base name
    # will result in the cached copy being used:
    mkdir(server_data, 'other')
    write(server_data, 'other', 'foo.txt', 'The wrong text.')
    path, is_temp = download(server_url+'other/foo.txt')
    assert_output(str(path), '/download-cache/foo.txt', N)
    assert_output(capture_print(cat, path), 'This is a foo text.', N)
    # Given a target path for the download, the utility will provide a copy of the
    # file at that location both when first downloading the file and when using a
    # cached copy:
    remove(cache, 'foo.txt')
    ls(cache)
    write(server_data, 'foo.txt', 'This is a foo text.')
    path, is_temp = download(server_url+'foo.txt',
                             path=join(target_dir, 'downloaded.txt'))
    assert_output(str(path), '/download-target/downloaded.txt', N)
    assert_output(capture_print(cat, path), 'This is a foo text.', N)
    _val = (is_temp)
    assert repr(_val) == 'False' or str(_val) == 'False'
    assert_output(capture_print(ls, cache), '- foo.txt', N)
    remove(path)
    write(server_data, 'foo.txt', 'The wrong text.')
    path, is_temp = download(server_url+'foo.txt',
                             path=join(target_dir, 'downloaded.txt'))
    assert_output(str(path), '/download-target/downloaded.txt', N)
    assert_output(capture_print(cat, path), 'This is a foo text.', N)
    _val = (is_temp)
    assert repr(_val) == 'False' or str(_val) == 'False'
    # In offline mode, downloads from any URL will be successful if the file is
    # found in the cache:
    download = Download(cache=cache, offline=True)
    assert_output(capture_print(cat, download(server_url + 'foo.txt')[0]), 'This is a foo text.', N)
    # Local resources will be cached just like any others since download caches are
    # sometimes used to create source distributions:
    remove(cache, 'foo.txt')
    ls(cache)
    write(server_data, 'foo.txt', 'This is a foo text.')
    download = Download(cache=cache)
    assert_output(capture_print(cat, download('file:' + join(server_data, 'foo.txt'), path=path)[0]), 'This is a foo text.', N)
    assert_output(capture_print(ls, cache), '- foo.txt', N)
    remove(cache, 'foo.txt')
    assert_output(capture_print(cat, download(join(server_data, 'foo.txt'), path=path)[0]), 'This is a foo text.', N)
    assert_output(capture_print(ls, cache), '- foo.txt', N)
    remove(cache, 'foo.txt')
    # However, resources with checksum mismatches will not be copied to the cache:
    try:
        download(server_url+'foo.txt', md5(b'The wrong text.').hexdigest())
        assert False, "Expected ChecksumError not raised"
    except Exception as _exc:  # noqa: BLE001 - the class
        # and message are pinned by the assertion below
        assert_output(str(_exc), "MD5 checksum mismatch downloading 'http://localhost/foo.txt'", N)
    ls(cache)
    remove(path)
    # If the file is completely missing it should notify the user of the error:
    try:
        download(server_url+'bar.txt')
        assert False, "Expected ...404... not raised"
    except Exception as _exc:  # noqa: BLE001 - the class
        # and message are pinned by the assertion below
        assert_output(str(_exc), '...404...', N)
    ls(cache)
    # Finally, let's see what happens if the download cache to be used doesn't exist
    # as a directory in the file system yet:
    try:
        Download(cache=join(cache, 'non-existent'))(server_url+'foo.txt')
        assert False, "Expected to be used as a download cache doesn't exist. not raised"
    except Exception as _exc:  # noqa: BLE001 - the class
        # and message are pinned by the assertion below
        assert_output(str(_exc), "to be used as a download cache doesn't exist.", N)
    # Using namespace sub-directories of the download cache
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #
    # It is common to store cached copies of downloaded files within sub-directories
    # of the download cache to keep some degree of order. For example, zc.buildout
    # stores downloaded distributions in a sub-directory named "dist". Those
    # sub-directories are also known as namespaces. So far, we haven't specified any
    # namespaces to use, so the download utility stored files directly inside the
    # download cache. Let's use a namespace "test" instead:
    download = Download(cache=cache, namespace='test')
    assert_output(str(download.cache_dir), '/download-cache/test', N)
    # The namespace sub-directory hasn't been created yet:
    ls(cache)
    # Downloading a file now creates the namespace sub-directory and places a copy
    # of the file inside it:
    path, is_temp = download(server_url+'foo.txt')
    assert_output(str(path), '/download-cache/test/foo.txt', N)
    assert_output(capture_print(ls, cache), 'd test', N)
    assert_output(capture_print(ls, cache, 'test'), '- foo.txt', N)
    assert_output(capture_print(cat, path), 'This is a foo text.', N)
    _val = (is_temp)
    assert repr(_val) == 'False' or str(_val) == 'False'
    # The next time we want to download that file, the copy from inside the cache
    # namespace is used. To see this clearly, we put a file with the same name but
    # different content both on the server and in the cache's root directory:
    write(server_data, 'foo.txt', 'The wrong text.')
    write(cache, 'foo.txt', 'The wrong text.')
    path, is_temp = download(server_url+'foo.txt')
    assert_output(str(path), '/download-cache/test/foo.txt', N)
    assert_output(capture_print(cat, path), 'This is a foo text.', N)
    rmdir(cache, 'test')
    remove(cache, 'foo.txt')
    write(server_data, 'foo.txt', 'This is a foo text.')
    # Using a hash of the URL as the filename in the cache
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #
    # So far, the base name of the downloaded file read from the URL has been used
    # for the name of the cached copy of the file. This may not be desirable in some
    # cases, for example when downloading files from different locations that have
    # the same base name due to some naming convention, or if the file content
    # depends on URL parameters. In such cases, an MD5 hash of the complete URL may
    # be used as the filename in the cache:
    download = Download(cache=cache, hash_name=True)
    path, is_temp = download(server_url+'foo.txt')
    assert_output(str(path), '/download-cache/<MD5 CHECKSUM>', N)
    assert_output(capture_print(cat, path), 'This is a foo text.', N)
    assert_output(capture_print(ls, cache), '- <MD5 CHECKSUM>', N)
    # The path was printed just to illustrate matters; we cannot know the real
    # checksum since we don't know which port the server happens to listen at when
    # the test is run, so we don't actually know the full URL of the file. Let's
    # check that the checksum actually belongs to the particular URL used:
    _val = (path.lower() ==
 join(cache, md5((server_url+'foo.txt').encode()).hexdigest()).lower())
    assert repr(_val) == 'True' or str(_val) == 'True'
    # The cached copy is used when downloading the file again:
    write(server_data, 'foo.txt', 'The wrong text.')
    _val = (path, is_temp) == download(server_url+'foo.txt')
    assert repr(_val) == 'True' or str(_val) == 'True'
    assert_output(capture_print(cat, path), 'This is a foo text.', N)
    assert_output(capture_print(ls, cache), '- <MD5 CHECKSUM>', N)
    # If we change the URL, even in such a way that it keeps the base name of the
    # file the same, the file will be downloaded again this time and put in the
    # cache under a different name:
    path2, is_temp = download(server_url+'other/foo.txt')
    assert_output(str(path2), '/download-cache/<MD5 CHECKSUM>', N)
    _val = (path == path2)
    assert repr(_val) == 'False' or str(_val) == 'False'
    _val = (path2.lower() ==
 join(cache, md5((server_url+'other/foo.txt').encode()).hexdigest()
      ).lower())
    assert repr(_val) == 'True' or str(_val) == 'True'
    assert_output(capture_print(cat, path), 'This is a foo text.', N)
    assert_output(capture_print(cat, path2), 'The wrong text.', N)
    assert_output(capture_print(ls, cache), """
- <MD5 CHECKSUM>
- <MD5 CHECKSUM>
""", N)
    remove(path)
    remove(path2)
    write(server_data, 'foo.txt', 'This is a foo text.')
    # Using the cache purely as a fall-back
    # -------------------------------------
    #
    # Sometimes it is desirable to try downloading a file from the net if at all
    # possible, and use the cache purely as a fall-back option when a server is
    # down or if we are in offline mode. This mode is only in effect if a download
    # cache is configured in the first place:
    download = Download(cache=cache, fallback=True)
    assert_output(str(download.cache_dir), '/download-cache/', N)
    # A downloaded file will be cached:
    ls(cache)
    path, is_temp = download(server_url+'foo.txt')
    assert_output(capture_print(ls, cache), '- foo.txt', N)
    assert_output(capture_print(cat, cache, 'foo.txt'), 'This is a foo text.', N)
    _val = (is_temp)
    assert repr(_val) == 'False' or str(_val) == 'False'
    # If the file cannot be served, the cached copy will be used:
    remove(server_data, 'foo.txt')
    try:
        Download()(server_url+'foo.txt') # doctest: +ELLIPSIS
    except Exception:  # noqa: BLE001 - fallback marker print;
        # the error type is not under test here
        print_('download error')
    else:
        print_('woops')
    # TODO assert: 'download error'
    path, is_temp = download(server_url+'foo.txt')
    assert_output(capture_print(cat, path), 'This is a foo text.', N)
    _val = (is_temp)
    assert repr(_val) == 'False' or str(_val) == 'False'
    # Similarly, if the file is served but we're in offline mode, we'll fall back to
    # using the cache:
    write(server_data, 'foo.txt', 'The wrong text.')
    _val = (get(server_url+'foo.txt'))
    assert repr(_val) == "'The wrong text.'" or str(_val) == "'The wrong text.'"
    offline_download = Download(cache=cache, offline=True, fallback=True)
    path, is_temp = offline_download(server_url+'foo.txt')
    assert_output(str(path), '/download-cache/foo.txt', N)
    assert_output(capture_print(cat, path), 'This is a foo text.', N)
    _val = (is_temp)
    assert repr(_val) == 'False' or str(_val) == 'False'
    # However, when downloading the file normally with the cache being used in
    # fall-back mode, the file will be downloaded from the net and the cached copy
    # will be replaced with the new content:
    assert_output(capture_print(cat, download(server_url + 'foo.txt')[0]), 'The wrong text.', N)
    assert_output(capture_print(cat, cache, 'foo.txt'), 'The wrong text.', N)
    # When trying to download a resource whose checksum does not match, the cached
    # copy will neither be used nor overwritten:
    write(server_data, 'foo.txt', 'This is a foo text.')
    try:
        download(server_url+'foo.txt', md5(b'The wrong text.').hexdigest())
        assert False, "Expected ChecksumError not raised"
    except Exception as _exc:  # noqa: BLE001 - the class
        # and message are pinned by the assertion below
        assert_output(str(_exc), "MD5 checksum mismatch downloading 'http://localhost/foo.txt'", N)
    assert_output(capture_print(cat, cache, 'foo.txt'), 'The wrong text.', N)
    # Configuring the download utility from buildout options
    # ------------------------------------------------------
    #
    # The configuration options explained so far derive from the build logic
    # implemented by the calling code. Other options configure the download utility
    # for use in a particular project or buildout run; they are read from the
    # ``buildout`` configuration section. The latter can be passed directly as the
    # first argument to the download utility's constructor.
    #
    # The location of the download cache is specified by the ``download-cache``
    # option:
    download = Download({'download-cache': cache}, namespace='cmmi')
    assert_output(str(download.cache_dir), '/download-cache/cmmi', N)
    # If the ``download-cache`` option specifies a relative path, it is understood
    # relative to the current working directory, or to the buildout directory if
    # that is given:
    download = Download({'download-cache': 'relative-cache'})
    assert_output(str(download.cache_dir), '/sample-buildout/relative-cache/', N)
    download = Download({'directory': join(sample_buildout, 'root'),
                         'download-cache': 'relative-cache'})
    assert_output(str(download.cache_dir), '/sample-buildout/root/relative-cache/', N)
    # Keyword parameters take precedence over the corresponding options:
    download = Download({'download-cache': cache}, cache=None)
    assert_output(str(download.cache_dir), 'None', N)
    # Whether to assume offline mode can be inferred from either the ``offline`` or
    # the ``install-from-cache`` option. As usual with zc.buildout, these options
    # must assume one of the values 'true' and 'false':
    download = Download({'offline': 'true'})
    _val = (download.offline)
    assert repr(_val) == 'True' or str(_val) == 'True'
    download = Download({'offline': 'false'})
    _val = (download.offline)
    assert repr(_val) == 'False' or str(_val) == 'False'
    download = Download({'install-from-cache': 'true'})
    _val = (download.offline)
    assert repr(_val) == 'True' or str(_val) == 'True'
    download = Download({'install-from-cache': 'false'})
    _val = (download.offline)
    assert repr(_val) == 'False' or str(_val) == 'False'
    # These two options are combined using logical 'or':
    download = Download({'offline': 'true', 'install-from-cache': 'false'})
    _val = (download.offline)
    assert repr(_val) == 'True' or str(_val) == 'True'
    download = Download({'offline': 'false', 'install-from-cache': 'true'})
    _val = (download.offline)
    assert repr(_val) == 'True' or str(_val) == 'True'
    # The ``offline`` keyword parameter takes precedence over both the ``offline``
    # and ``install-from-cache`` options:
    download = Download({'offline': 'true'}, offline=False)
    _val = (download.offline)
    assert repr(_val) == 'False' or str(_val) == 'False'
    download = Download({'install-from-cache': 'false'}, offline=True)
    _val = (download.offline)
    assert repr(_val) == 'True' or str(_val) == 'True'
    # Regressions
    # -----------
    #
    # MD5 checksum calculation needs to be reliable on all supported systems, which
    # requires text files to be treated as binary to avoid implicit line-ending
    # conversions:
    text = 'First line of text.\r\nSecond line.\r\n'
    with open(join(server_data, 'foo.txt'), 'wb') as f:
        _ = f.write(text.encode())
    path, is_temp = Download()(server_url+'foo.txt',
                               md5(text.encode()).hexdigest())
    remove(path)
    # When "downloading" a directory given by file-system path or ``file:`` URL and
    # using a download cache at the same time, the cached directory wasn't handled
    # correctly. Consequently, the cache was defeated and an attempt to cache the
    # directory a second time broke. This is how it should work:
    download = Download(cache=cache)
    dirpath = join(server_data, 'some_directory')
    mkdir(dirpath)
    dest, _ = download(dirpath)
    # If we now modify the source tree, the second download will produce the
    # original one from the cache:
    mkdir(join(dirpath, 'foo'))
    assert_output(capture_print(ls, dirpath), 'd foo', N)
    dest, _ = download(dirpath)
    ls(dest)
    # Clean up
    # --------
    #
    # We should have cleaned up all temporary files created by downloading things:
    ls(tempfile.tempdir)
    # Reset the global temporary directory:
    tempfile.tempdir = old_tempdir

def test_extends_cache(easy_install_env):
    buildout = easy_install_env['buildout']
    cat = easy_install_env['cat']
    cd = easy_install_env['cd']
    join = easy_install_env['join']
    ls = easy_install_env['ls']
    mkdir = easy_install_env['mkdir']
    print_ = easy_install_env['print_']
    remove = easy_install_env['remove']
    rmdir = easy_install_env['rmdir']
    sample_buildout = easy_install_env['sample_buildout']
    start_server = easy_install_env['start_server']
    system = easy_install_env['system']
    tmpdir = easy_install_env['tmpdir']
    write = easy_install_env['write']

    # Caching extended configuration
    # ==============================
    #
    # As mentioned in the general buildout documentation, configuration files can
    # extend each other, including the ability to download configuration being
    # extended from a URL. If desired, zc.buildout caches downloaded configuration
    # in order to be able to use it when run offline.
    #
    # As we're going to talk about downloading things, let's start an HTTP server.
    # Also, all of the following will take place inside the sample buildout.
    server_data = tmpdir('server_data')
    server_url = start_server(server_data)
    cd(sample_buildout)
    # We also use a fresh directory for temporary files in order to make sure that
    # all temporary files have been cleaned up in the end:
    import tempfile
    old_tempdir = tempfile.tempdir
    tempfile.tempdir = tmpdir('tmp')
    # Basic use of the extends cache
    # ------------------------------
    #
    # We put some base configuration on a server and reference it from a sample
    # buildout:
    write(server_data, 'base.cfg', """\
    [buildout]
    parts =
    foo = bar
    """)
    write('buildout.cfg', f"""\
    [buildout]
    extends = {server_url}base.cfg
    """)
    # When trying to run this buildout offline, we'll find that we cannot read all
    # of the required configuration:
    assert_output(system(buildout + ' -o'), """
While:
  Initializing.
Error: Couldn't download 'http://localhost/base.cfg' in offline mode.
Run buildout once in online mode with a cache directory
configured: 'extends-cache' for configuration files,
'download-cache' for other files; the download is then
reused from the cache while offline.
""", N)
    # Trying the same online, we can:
    assert_output(system(buildout), """
Section `buildout` contains unused option(s): 'foo'.
This may be an indication for either a typo in the option's name or a bug in the used recipe.
""", N)
    # As long as we haven't said anything about caching downloaded configuration,
    # nothing gets cached. Offline mode will still cause the buildout to fail:
    assert_output(system(buildout + ' -o'), """
While:
  Initializing.
Error: Couldn't download 'http://localhost/base.cfg' in offline mode.
Run buildout once in online mode with a cache directory
configured: 'extends-cache' for configuration files,
'download-cache' for other files; the download is then
reused from the cache while offline.
""", N)
    # Let's now specify a cache for base configuration files. This cache is
    # different from the download cache used by recipes for caching distributions
    # and other files; one might, however, use a namespace subdirectory of the
    # download cache for it. The configuration cache we specify will be created when
    # running buildout and the base.cfg file will be put in it (with the file name
    # being a hash of the complete URL):
    mkdir('cache')
    write('buildout.cfg', f"""\
    [buildout]
    extends = {server_url}base.cfg
    extends-cache = cache
    """)
    assert_output(system(buildout), """
Section `buildout` contains unused option(s): 'foo'.
This may be an indication for either a typo in the option's name or a bug in the used recipe.
""", N)
    cache = join(sample_buildout, 'cache')
    assert_output(capture_print(ls, cache), '-  <MD5 CHECKSUM>', N)
    import os
    assert_output(capture_print(cat, cache, os.listdir(cache)[0]), """
[buildout]
parts =
foo = bar
""", N)
    # We can now run buildout offline as it will read base.cfg from the cache:
    assert_output(system(buildout + ' -o'), """
Section `buildout` contains unused option(s): 'foo'.
This may be an indication for either a typo in the option's name or a bug in the used recipe.
""", N)
    # The cache is being used purely as a fall-back in case we are offline or don't
    # have access to a configuration file to be downloaded. As long as we are
    # online, buildout attempts to download a fresh copy of each file even if a
    # cached copy of the file exists. To see this, we put different configuration in
    # the same place on the server and run buildout in offline mode so it takes
    # base.cfg from the cache:
    write(server_data, 'base.cfg', """\
    [buildout]
    parts =
    bar = baz
    """)
    assert_output(system(buildout + ' -o'), """
Section `buildout` contains unused option(s): 'foo'.
This may be an indication for either a typo in the option's name or a bug in the used recipe.
""", N)
    # .. verify same behavior for install-from-cache:
    assert_output(system(buildout + ' install-from-cache=true download-cache=.'), """
Section `buildout` contains unused option(s): 'foo'.
This may be an indication for either a typo in the option's name or a bug in the used recipe.
""", N)
    # In online mode, buildout will download and use the modified version:
    assert_output(system(buildout), """
Section `buildout` contains unused option(s): 'bar'.
This may be an indication for either a typo in the option's name or a bug in the used recipe.
""", N)
    # Trying offline mode again, the new version will be used as it has been put in
    # the cache now:
    assert_output(system(buildout + ' -o'), """
Section `buildout` contains unused option(s): 'bar'.
This may be an indication for either a typo in the option's name or a bug in the used recipe.
""", N)
    # Clean up:
    rmdir(cache)
    # Specifying extends cache and offline mode
    # -----------------------------------------
    #
    # Normally, the values of buildout options such as the location of a download
    # cache or whether to use offline mode are determined by first reading the
    # user's default configuration, updating it with the project's configuration and
    # finally applying command-line options. User and project configuration are
    # assembled by reading a file such as ``~/.buildout/default.cfg``,
    # ``buildout.cfg`` or a URL given on the command line, recursively (depth-first)
    # downloading any base configuration specified by the ``buildout:extends``
    # option read from each of those config files, and finally evaluating each
    # config file to provide default values for options not yet read.
    #
    # This works fine for all options that do not influence how configuration is
    # downloaded in the first place. The ``extends-cache`` and ``offline`` options,
    # however, are treated differently from the procedure described in order to make
    # it simple and obvious to see where a particular configuration file came from
    # under any particular circumstances.
    #
    # - Offline and extends-cache settings are read from the two root config files
    #   exclusively. Otherwise one could construct configuration files that, when
    #   read, imply that they should have been read from a different source than
    #   they have. Also, specifying the extends cache within a file that might have
    #   to be taken from the cache before being read wouldn't make a lot of sense.
    #
    # - Offline and extends-cache settings given by the user's defaults apply to the
    #   process of assembling the project's configuration. If no extends cache has
    #   been specified by the user's default configuration, the project's root
    #   config file must be available, be it from disk or from the net.
    #
    # - Offline mode turned on by the ``-o`` command line option is honored from
    #   the beginning even though command line options are applied to the
    #   configuration last. If offline mode is not requested by the command line, it
    #   may be switched on by either the user's or the project's config root.
    #
    # Extends cache
    # ~~~~~~~~~~~~~
    #
    # Let's see the above rules in action. We create a new home directory for our
    # user and write user and project configuration that recursively extends online
    # bases, using different caches:
    mkdir('home')
    mkdir('home', '.buildout')
    mkdir('cache')
    mkdir('user-cache')
    home=join(sample_buildout, 'home')
    env={'HOME': home, 'USERPROFILE': home}
    import functools
    system = functools.partial(system, env=env)
    write('home', '.buildout', 'default.cfg', """\
    [buildout]
    extends = fancy_default.cfg
    extends-cache = user-cache
    """)
    write('home', '.buildout', 'fancy_default.cfg', f"""\
    [buildout]
    extends = {server_url}base_default.cfg
    """)
    write(server_data, 'base_default.cfg', """\
    [buildout]
    foo = bar
    offline = false
    """)
    write('buildout.cfg', """\
    [buildout]
    extends = fancy.cfg
    extends-cache = cache
    """)
    write('fancy.cfg', f"""\
    [buildout]
    extends = {server_url}base.cfg
    """)
    write(server_data, 'base.cfg', """\
    [buildout]
    parts =
    offline = false
    """)
    # Buildout will now assemble its configuration from all of these 6 files,
    # defaults first. The online resources end up in the respective extends caches:
    assert_output(system(buildout), """
Section `buildout` contains unused option(s): 'foo'.
This may be an indication for either a typo in the option's name or a bug in the used recipe.
""", N)
    assert_output(capture_print(ls, 'user-cache'), '-  <MD5 CHECKSUM>', N)
    assert_output(capture_print(cat, 'user-cache', os.listdir('user-cache')[0]), """
[buildout]
foo = bar
offline = false
""", N)
    assert_output(capture_print(ls, 'cache'), '-  <MD5 CHECKSUM>', N)
    assert_output(capture_print(cat, 'cache', os.listdir('cache')[0]), """
[buildout]
parts =
offline = false
""", N)
    # If, on the other hand, the extends caches are specified in files that get
    # extended themselves, they won't be used for assembling the configuration they
    # belong to (user's or project's, resp.). The extends cache specified by the
    # user's defaults does, however, apply to downloading project configuration.
    # Let's rewrite the config files, clean out the caches and re-run buildout:
    write('home', '.buildout', 'default.cfg', """\
    [buildout]
    extends = fancy_default.cfg
    """)
    write('home', '.buildout', 'fancy_default.cfg', f"""\
    [buildout]
    extends = {server_url}base_default.cfg
    extends-cache = user-cache
    """)
    write('buildout.cfg', """\
    [buildout]
    extends = fancy.cfg
    """)
    write('fancy.cfg', f"""\
    [buildout]
    extends = {server_url}base.cfg
    extends-cache = cache
    """)
    remove('user-cache', os.listdir('user-cache')[0])
    remove('cache', os.listdir('cache')[0])
    assert_output(system(buildout), """
Section `buildout` contains unused option(s): 'foo'.
This may be an indication for either a typo in the option's name or a bug in the used recipe.
""", N)
    assert_output(capture_print(ls, 'user-cache'), '-  <MD5 CHECKSUM>', N)
    assert_output(capture_print(cat, 'user-cache', os.listdir('user-cache')[0]), """
[buildout]
parts =
offline = false
""", N)
    ls('cache')
    # Clean up:
    rmdir('user-cache')
    rmdir('cache')
    # Offline mode and installation from cache
    # ----------------------------------------
    #
    # If we run buildout in offline mode now, it will fail because it cannot get at
    # the remote configuration file needed by the user's defaults:
    assert_output(system(buildout + ' -o'), """
While:
  Initializing.
Error: Couldn't download 'http://localhost/base_default.cfg' in offline mode.
Run buildout once in online mode with a cache directory
configured: 'extends-cache' for configuration files,
'download-cache' for other files; the download is then
reused from the cache while offline.
""", N)
    # Let's now successively turn on offline mode by different parts of the
    # configuration and see when buildout applies this setting in each case:
    write('home', '.buildout', 'default.cfg', """\
    [buildout]
    extends = fancy_default.cfg
    offline = true
    """)
    assert_output(system(buildout), """
While:
  Initializing.
Error: Couldn't download 'http://localhost/base_default.cfg' in offline mode.
Run buildout once in online mode with a cache directory
configured: 'extends-cache' for configuration files,
'download-cache' for other files; the download is then
reused from the cache while offline.
""", N)
    write('home', '.buildout', 'default.cfg', """\
    [buildout]
    extends = fancy_default.cfg
    """)
    write('home', '.buildout', 'fancy_default.cfg', f"""\
    [buildout]
    extends = {server_url}base_default.cfg
    offline = true
    """)
    assert_output(system(buildout), """
While:
  Initializing.
Error: Couldn't download 'http://localhost/base.cfg' in offline mode.
Run buildout once in online mode with a cache directory
configured: 'extends-cache' for configuration files,
'download-cache' for other files; the download is then
reused from the cache while offline.
""", N)
    write('home', '.buildout', 'fancy_default.cfg', f"""\
    [buildout]
    extends = {server_url}base_default.cfg
    """)
    write('buildout.cfg', """\
    [buildout]
    extends = fancy.cfg
    offline = true
    """)
    assert_output(system(buildout), """
While:
  Initializing.
Error: Couldn't download 'http://localhost/base.cfg' in offline mode.
Run buildout once in online mode with a cache directory
configured: 'extends-cache' for configuration files,
'download-cache' for other files; the download is then
reused from the cache while offline.
""", N)
    write('buildout.cfg', """\
    [buildout]
    extends = fancy.cfg
    """)
    write('fancy.cfg', f"""\
    [buildout]
    extends = {server_url}base.cfg
    offline = true
    """)
    assert_output(system(buildout), """
Section `buildout` contains unused option(s): 'foo'.
This may be an indication for either a typo in the option's name or a bug in the used recipe.
""", N)
    # The ``install-from-cache`` option is treated accordingly:
    write('home', '.buildout', 'default.cfg', """\
    [buildout]
    extends = fancy_default.cfg
    install-from-cache = true
    """)
    assert_output(system(buildout), """
While:
  Initializing.
Error: Couldn't download 'http://localhost/base_default.cfg' in offline mode.
Run buildout once in online mode with a cache directory
configured: 'extends-cache' for configuration files,
'download-cache' for other files; the download is then
reused from the cache while offline.
""", N)
    write('home', '.buildout', 'default.cfg', """\
    [buildout]
    extends = fancy_default.cfg
    """)
    write('home', '.buildout', 'fancy_default.cfg', f"""\
    [buildout]
    extends = {server_url}base_default.cfg
    install-from-cache = true
    """)
    assert_output(system(buildout), """
While:
  Initializing.
Error: Couldn't download 'http://localhost/base.cfg' in offline mode.
Run buildout once in online mode with a cache directory
configured: 'extends-cache' for configuration files,
'download-cache' for other files; the download is then
reused from the cache while offline.
""", N)
    write('home', '.buildout', 'fancy_default.cfg', f"""\
    [buildout]
    extends = {server_url}base_default.cfg
    """)
    write('buildout.cfg', """\
    [buildout]
    extends = fancy.cfg
    install-from-cache = true
    """)
    assert_output(system(buildout), """
While:
  Initializing.
Error: Couldn't download 'http://localhost/base.cfg' in offline mode.
Run buildout once in online mode with a cache directory
configured: 'extends-cache' for configuration files,
'download-cache' for other files; the download is then
reused from the cache while offline.
""", N)
    write('buildout.cfg', """\
    [buildout]
    extends = fancy.cfg
    """)
    write('fancy.cfg', f"""\
    [buildout]
    extends = {server_url}base.cfg
    install-from-cache = true
    """)
    assert_output(system(buildout), """
While:
  Installing.
  Checking for upgrades.
An internal error occurred ...
...
ValueError: install_from_cache set to true with no download cache
""", N)
    rmdir('home', '.buildout')
    # Newest and non-newest behavior for extends cache
    # -------------------------------------------------
    #
    # While offline mode forbids network access completely, 'newest' mode determines
    # whether to look for updated versions of a resource even if some version of it
    # is already present locally. If we run buildout in newest mode
    # (``newest = true``), the configuration files are updated with each run:
    mkdir("cache")
    write(server_data, 'base.cfg', """\
    [buildout]
    parts =
    """)
    write('buildout.cfg', f"""\
    [buildout]
    extends-cache = cache
    extends = {server_url}base.cfg
    """)
    print_(system(buildout))
    assert_output(capture_print(ls, 'cache'), '-  <MD5 CHECKSUM>', N)
    assert_output(capture_print(cat, 'cache', os.listdir(cache)[0]), """
[buildout]
parts =
""", N)
    # A change to ``base.cfg`` is picked up on the next buildout run:
    write(server_data, 'base.cfg', """\
    [buildout]
    parts =
    foo = bar
    """)
    assert_output(system(buildout + ' -n'), """
Section `buildout` contains unused option(s): 'foo'.
This may be an indication for either a typo in the option's name or a bug in the used recipe.
""", N)
    assert_output(capture_print(cat, 'cache', os.listdir(cache)[0]), """
[buildout]
parts =
foo = bar
""", N)
    # In contrast, when not using ``newest`` mode (``newest = false``), the files
    # already present in the extends cache will not be updated:
    write(server_data, 'base.cfg', """\
    [buildout]
    parts =
    """)
    assert_output(system(buildout + ' -N'), """
Section `buildout` contains unused option(s): 'foo'.
This may be an indication for either a typo in the option's name or a bug in the used recipe.
""", N)
    assert_output(capture_print(cat, 'cache', os.listdir(cache)[0]), """
[buildout]
parts =
foo = bar
""", N)
    # Even when updating base configuration files with a buildout run, any given
    # configuration file will be downloaded only once during that particular run. If
    # some base configuration file is extended more than once, its cached copy is
    # used:
    write(server_data, 'baseA.cfg', f"""\
    [buildout]
    extends = {server_url}base.cfg
    foo = bar
    """)
    write(server_data, 'baseB.cfg', f"""\
    [buildout]
    extends-cache = cache
    extends = {server_url}base.cfg
    bar = foo
    """)
    write('buildout.cfg', f"""\
    [buildout]
    extends-cache = cache
    newest = true
    extends = {server_url}baseA.cfg {server_url}baseB.cfg
    """)
    assert_output(system(buildout + ' -n'), """
Section `buildout` contains unused option(s): 'bar' 'foo'.
This may be an indication for either a typo in the option's name or a bug in the used recipe.
""", N)
    # (XXX We patch download utility's API to produce readable output for the test;
    # a better solution would re-use the logging already done by the utility.)
    import zc.buildout.download
    old_download = zc.buildout.download.Download.download
    def wrapper_download(self, url, md5sum=None, path=None):
      print_(f"The URL {url} was downloaded.")
      return old_download(self, url, md5sum, path)
    zc.buildout.download.Download.download = wrapper_download
    assert_output(capture_print(lambda: zc.buildout.buildout.main([])), """
The URL http://localhost/baseA.cfg was downloaded.
The URL http://localhost/base.cfg was downloaded.
The URL http://localhost/baseB.cfg was downloaded.
...
Section `buildout` contains unused option(s): 'bar' 'foo'.
This may be an indication for either a typo in the option's name or a bug in the used recipe.
""", N)
    zc.buildout.download.Download.download = old_download
    # The deprecated ``extended-by`` option
    # -------------------------------------
    #
    # The ``buildout`` section used to recognize an option named ``extended-by``
    # that was deprecated at some point and removed in the 1.5 line. Since ignoring
    # this option silently was considered harmful as a matter of principle, a
    # UserError is raised if that option is encountered now:
    write(server_data, 'base.cfg', """\
    [buildout]
    parts =
    extended-by = foo.cfg
    """)
    assert_output(system(buildout), """
While:
  Initializing.
Error: No-longer supported "extended-by" option found in http://localhost/base.cfg.
""", N)
    # Reporting cached locations for downloads of faulty config files
    # ---------------------------------------------------------------
    #
    # A downloaded config file might be invalid. A cancelled buildout run, an
    # accidentally gzip-encoded download and so on.
    write(server_data, 'faulty.cfg', """\
    This is definitively not
    a proper() config file.
    """)
    write('buildout.cfg', f"""\
    [buildout]
    extends = {server_url}faulty.cfg
    """)
    assert_output(system(buildout), """
While:
  Initializing.
...
... File contains no section headers.
file: http://localhost/faulty.cfg (downloaded as ...), line: 1
'This is definitively not\\n'
""", N)
    # Failing if extends-cache contains ${section:variable}
    # -----------------------------------------------------
    #
    # Because extends-cache is used to download extends, it may not contain ${section:variable}
    # as the state of all variables cannot be computed before all extends have been loaded.
    write(server_data, 'proper.cfg', """\
    [buildout]
    dummy = fjhfj
    """)
    write('buildout.cfg', f"""\
    [buildout]
    extends = {server_url}proper.cfg
    extends-cache = ${{buildout:dummy}}
    """)
    assert_output(system(buildout), """
While:
  Initializing.
...
...ValueError: extends-cache '${buildout:dummy}' may not contain ${section:variable} to expand.
""", N)
    # Clean up
    # --------
    #
    # We should have cleaned up all temporary files created by downloading things:
    ls(tempfile.tempdir)
    # Reset the global temporary directory:
    tempfile.tempdir = old_tempdir

def test_testing_bugfix(easy_install_env):
    # Bug fixes in zc.buildout.testing
    # ================================
    #
    # Logging handler which did not get deleted
    # -----------------------------------------
    #
    # The buildout testing set up runs a buildout which adds a
    # ``logging.StreamHandler`` to the root logger. But tear down did not
    # remove it. This can disturb other tests of packages reusing
    # zc.buildout.testing.
    #
    # The handlers before calling set up are:
    import logging
    count = len(logging.getLogger().handlers)
    assert_output(capture_print(lambda: print(logging.getLogger().handlers)), '[<...NullHandler...>]', N)
    # After calling it, a ``logging.StreamHandler`` was added:
    import zc.buildout.testing  # isort: skip
    import doctest  # isort: skip
    test = doctest.DocTestParser().get_doctest(
        '>>> x', {}, 'foo', 'foo.py', 0)
    zc.buildout.testing.buildoutSetUp(test)
    _val = (len(logging.getLogger().handlers) == count + 1)
    assert repr(_val) == 'True' or str(_val) == 'True'
    assert_output(capture_print(lambda: print(logging.getLogger().handlers)), '[<...NullHandler...StreamHandler...>]', N)
    # But tear down removes the new logging handler:
    zc.buildout.testing.buildoutTearDown(test)
    _val = (len(logging.getLogger().handlers) == count)
    assert repr(_val) == 'True' or str(_val) == 'True'
    assert_output(capture_print(lambda: print(logging.getLogger().handlers)), '[<...NullHandler...>]', N)
