Test-Runner Recipe
==================

The test-runner recipe, zc.recipe.testrunner, creates a test runner
for a project.

The rest-runner recipe has 2 options:

- The distributions option takes the names of the distributions to be tested.
  These are not installed by the recipe. They must be installed by
  some other recipe.  This option is required.

- The script option gives the name of the script to generate, in the
  buildout bin directory.  Of the option isn't used, the part name
  will be used.

(Note that, at this time, due to limitations in the Zope test runner,
 the distributions cannot be zip files. TODO: Fix the test runner!)

To illustrate this, we'll create a project in our sample buildout:

    >>> mkdir(sample_buildout, 'demo')
    >>> write(sample_buildout, 'demo', 'tests.py',
    ... '''
    ... import unittest
    ...
    ... class TestSomething(unittest.TestCase):
    ...    def test_something(self):
    ...        pass
    ...
    ... def test_suite():
    ...     return unittest.makeSuite(TestSomething)
    ... ''')

    >>> write(sample_buildout, 'demo', 'setup.py',
    ... """
    ... from setuptools import setup
    ... 
    ... setup(name = "demo")
    ... """)

    >>> write(sample_buildout, 'demo', 'README.txt', '')

We'll update our buildout to install the demo project as a
develop egg and to create the test script:

    >>> write(sample_buildout, 'buildout.cfg',
    ... """
    ... [buildout]
    ... develop = demo
    ... parts = testdemo
    ...
    ... [testdemo]
    ... recipe = zc.recipe.testrunner
    ... distributions = demo
    ... script = test
    ... """)

Now when we run the buildout:

    >>> import os
    >>> os.chdir(sample_buildout)
    >>> print system(os.path.join(sample_buildout, 'bin', 'buildout')),

We get a test script installed in our bin directory:

    >>> ls(sample_buildout, 'bin')
    -  buildout
    -  test

We can run the test script to run our demo test:

    >>> print system(os.path.join(sample_buildout, 'bin', 'test')),
    Running unit tests:
      Ran 1 tests with 0 failures and 0 errors in 0.000 seconds.

If we leave the script option out of the configuration, then the test
script will get it's name from the part:

    >>> write(sample_buildout, 'buildout.cfg',
    ... """
    ... [buildout]
    ... develop = demo
    ... parts = testdemo
    ...
    ... [testdemo]
    ... recipe = zc.recipe.testrunner
    ... distributions = demo
    ... """)

    >>> print system(os.path.join(sample_buildout, 'bin', 'buildout')),

    >>> ls(sample_buildout, 'bin')
    -  buildout
    -  testdemo

We can run the test script to run our demo test:

    >>> print system(os.path.join(sample_buildout, 'bin', 'testdemo')),
    Running unit tests:
      Ran 1 tests with 0 failures and 0 errors in 0.000 seconds.
