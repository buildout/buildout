Test-Runner Recipe
==================

The test-runner recipe, zc.recipe.testrunner, creates a test runner
for a project.

The test-runner recipe has 3 options:

eggs
    The eggs option specified a list of eggs to test given as one ore
    more setuptools requirement strings.  Each string must be given on
    a separate line.

script
    The script option gives the name of the script to generate, in the
    buildout bin directory.  Of the option isn't used, the part name
    will be used.

extra-paths
    One or more extra paths to include in the generated test script.


(Note that, at this time, due to limitations in the Zope test runner,
 the distributions cannot be zip files. TODO: Fix the test runner!)

To illustrate this, we'll create a pair of projects in our sample
buildout:

    >>> mkdir(sample_buildout, 'demo')
    >>> mkdir(sample_buildout, 'demo', 'demo')
    >>> write(sample_buildout, 'demo', 'demo', '__init__.py', '')
    >>> write(sample_buildout, 'demo', 'demo', 'tests.py',
    ... '''
    ... import unittest
    ...
    ... class TestDemo(unittest.TestCase):
    ...    def test(self):
    ...        pass
    ...
    ... def test_suite():
    ...     return unittest.makeSuite(TestDemo)
    ... ''')

    >>> write(sample_buildout, 'demo', 'setup.py',
    ... """
    ... from setuptools import setup
    ... 
    ... setup(name = "demo")
    ... """)

    >>> write(sample_buildout, 'demo', 'README.txt', '')

    >>> mkdir(sample_buildout, 'demo2')
    >>> mkdir(sample_buildout, 'demo2', 'demo2')
    >>> write(sample_buildout, 'demo2', 'demo2', '__init__.py', '')
    >>> write(sample_buildout, 'demo2', 'demo2', 'tests.py',
    ... '''
    ... import unittest
    ...
    ... class Demo2Tests(unittest.TestCase):
    ...    def test2(self):
    ...        pass
    ...
    ... def test_suite():
    ...     return unittest.makeSuite(Demo2Tests)
    ... ''')

    >>> write(sample_buildout, 'demo2', 'setup.py',
    ... """
    ... from setuptools import setup
    ... 
    ... setup(name = "demo2", install_requires= ['demoneeded'])
    ... """)

    >>> write(sample_buildout, 'demo2', 'README.txt', '')

Demo 2 depends on demoneeded:

    >>> mkdir(sample_buildout, 'demoneeded')
    >>> mkdir(sample_buildout, 'demoneeded', 'demoneeded')
    >>> write(sample_buildout, 'demoneeded', 'demoneeded', '__init__.py', '')
    >>> write(sample_buildout, 'demoneeded', 'demoneeded', 'tests.py',
    ... '''
    ... import unittest
    ...
    ... class TestNeeded(unittest.TestCase):
    ...    def test_needed(self):
    ...        pass
    ...
    ... def test_suite():
    ...     return unittest.makeSuite(TestNeeded)
    ... ''')

    >>> write(sample_buildout, 'demoneeded', 'setup.py',
    ... """
    ... from setuptools import setup
    ... 
    ... setup(name = "demoneeded")
    ... """)

    >>> write(sample_buildout, 'demoneeded', 'README.txt', '')

We'll update our buildout to install the demo project as a
develop egg and to create the test script:

    >>> write(sample_buildout, 'buildout.cfg',
    ... """
    ... [buildout]
    ... develop = demo demoneeded demo2
    ... parts = testdemo
    ... offline = true
    ...
    ... [testdemo]
    ... recipe = zc.recipe.testrunner
    ... eggs = 
    ...    demo
    ...    demo2
    ... script = test
    ... """)

Note that we specified both demo and demo2 in the eggs
option and that we put them on separate lines.

We also specified the offline option to run the buildout in offline mode.

Now when we run the buildout:

    >>> import os
    >>> os.chdir(sample_buildout)
    >>> print system(os.path.join(sample_buildout, 'bin', 'buildout') + ' -q'),

We get a test script installed in our bin directory:

    >>> ls(sample_buildout, 'bin')
    -  buildout
    -  test

We can run the test script to run our demo test:

    >>> print system(os.path.join(sample_buildout, 'bin', 'test') + ' -vv'),
    Running tests at level 1
    Running unit tests:
      Running:
     test (demo.tests.TestDemo)
     test2 (demo2.tests.Demo2Tests)
      Ran 2 tests with 0 failures and 0 errors in 0.000 seconds.

Note that we didn't run the demoneeded tests.  Tests are only run for
the eggs listed, not for their dependencies.

If we leave the script option out of the configuration, then the test
script will get it's name from the part:

    >>> write(sample_buildout, 'buildout.cfg',
    ... """
    ... [buildout]
    ... develop = demo
    ... parts = testdemo
    ... offline = true
    ...
    ... [testdemo]
    ... recipe = zc.recipe.testrunner
    ... eggs = demo
    ... """)

    >>> print system(os.path.join(sample_buildout, 'bin', 'buildout') + ' -q'),

    >>> ls(sample_buildout, 'bin')
    -  buildout
    -  testdemo

We can run the test script to run our demo test:

    >>> print system(os.path.join(sample_buildout, 'bin', 'testdemo') + ' -q'),
    Running unit tests:
      Ran 1 tests with 0 failures and 0 errors in 0.000 seconds.

If we need to include other paths in our test script, we can use the
extra-paths option to specify them:

    >>> write(sample_buildout, 'buildout.cfg',
    ... """
    ... [buildout]
    ... develop = demo
    ... parts = testdemo
    ... offline = true
    ...
    ... [testdemo]
    ... recipe = zc.recipe.testrunner
    ... eggs = demo
    ... extra-paths = /usr/local/zope/lib/python
    ... """)

    >>> print system(os.path.join(sample_buildout, 'bin', 'buildout') + ' -q'),

    >>> cat(sample_buildout, 'bin', 'testdemo')
    #!/usr/local/bin/python2.4
    <BLANKLINE>
    import sys
    sys.path[0:0] = [
      '/sample-buildout/demo',
      '/sample-buildout/eggs/zope.testing-3.0-py2.3.egg',
      '/usr/local/zope/lib/python',
      ]
    <BLANKLINE>
    import zope.testing.testrunner
    <BLANKLINE>
    if __name__ == '__main__':
        zope.testing.testrunner.run([
      '--test-path', '/sample-buildout/demo',
      ])
