Installation of distributions as eggs
=====================================

The zc.recipe.egg recipe can be used to install various types if
distutils distributions as eggs.  It takes a number of options:

distribution
   The distribution specifies the distribution requirement.

   This is a requirement as defined by setuptools.

   If not specified, the distribution defaults to the part name.

   Multiple requirements can be given, separated by newlines.  Each
   requirement has to be on a separate line.

find-links
   A list of URLs, files, or directories to search for distributions.

index
   The URL of an index server, or almost any other valid URL. :)

   If not specified, the Python Package Index,
   http://cheeseshop.python.org/pypi, is used.  You can specify an
   alternate index with this option.  If you use the links option and
   if the links point to the needed distributions, then the index can
   be anything and will be largely ignored.  In the examples, here,
   we'll just point to an empty directory on our link server.  This 
   will make our examples run a little bit faster.

python
   The name of a section to get the Python executable from.
   If not specified, then the buildout python option is used.  The
   Python executable is found in the executable option of the named
   section. 

unzip
   The value of this option must be either true or false. If the value
   is true, then the installed egg will be unzipped. Note that this is
   only effective when an egg is installed.  If a zipped egg already 
   exists in the eggs directory, it will not be unzipped.


We have a link server that has a number of eggs:

    >>> print get(link_server),
    <html><body>
    <a href="demo-0.1-py2.3.egg">demo-0.1-py2.3.egg</a><br>
    <a href="demo-0.2-py2.3.egg">demo-0.2-py2.3.egg</a><br>
    <a href="demo-0.3-py2.3.egg">demo-0.3-py2.3.egg</a><br>
    <a href="demoneeded-1.0-py2.3.egg">demoneeded-1.0-py2.3.egg</a><br>
    <a href="demoneeded-1.1-py2.3.egg">demoneeded-1.1-py2.3.egg</a><br>
    <a href="index/">index/</a><br>
    <a href="other-1.0-py2.3.egg">other-1.0-py2.3.egg</a><br>
    </body></html>


We have a sample buildout.  Let's update it's configuration file to
install the demo package. 

    >>> write(sample_buildout, 'buildout.cfg',
    ... """
    ... [buildout]
    ... parts = demo
    ...
    ... [demo]
    ... recipe = zc.recipe.egg
    ... distribution = demo<0.3
    ... find-links = %(server)s
    ... index = %(server)s/index
    ... """ % dict(server=link_server))

In this example, we limited ourself to revisions before 0.3. We also
specified where to find distributions using the find-links option.

Let's run the buildout:

    >>> import os
    >>> os.chdir(sample_buildout)
    >>> buildout = os.path.join(sample_buildout, 'bin', 'buildout')
    >>> print system(buildout),
    
Now, if we look at the buildout eggs directory:

    >>> ls(sample_buildout, 'eggs')
    -  demo-0.2-py2.3.egg
    -  demoneeded-1.1-py2.3.egg

We see that we got an egg for demo that met the requirement, as well
as the egg for demoneeded, wich demo requires.  (We also see an egg
link for the recipe.  This egg link was actually created as part of
the sample buildout setup. Normally, when using the recipe, you'll get
a regular egg installation.)

The demo egg also defined a script and we see that the script was
installed as well:

    >>> ls(sample_buildout, 'bin')
    -  buildout
    -  demo
    -  py_demo

Here, in addition to the buildout script, we see the demo script,
demo, and we see a script, py_demo, for giving us a Python prompt with
the path for demo and any eggs it depends on included in sys.path.
This is useful for testing.

If we run the demo script, it prints out some minimal data:

    >>> print system(os.path.join(sample_buildout, 'bin', 'demo')),
    2 1

The value it prints out happens to be some values defined in the
modules installed.

We can also run the py_demo script.  Here we'll just print out
the bits if the path added to reflect the eggs:

    >>> print system(os.path.join(sample_buildout, 'bin', 'py_demo'),
    ... """for p in sys.path[:2]:
    ...        print p
    ... """).replace('>>> ', '').replace('... ', ''),
    ... # doctest: +ELLIPSIS
    <BLANKLINE>
    /tmp/tmpcy8MvGbuildout-tests/eggs/demo-0.2-py2.3.egg
    /tmp/tmpcy8MvGbuildout-tests/eggs/demoneeded-1.0-py2.3.egg
    <BLANKLINE>

The recipe gets the most recent distribution that satisfies the
specification. For example, We remove the restriction on demo:

    >>> write(sample_buildout, 'buildout.cfg',
    ... """
    ... [buildout]
    ... parts = demo
    ...
    ... [demo]
    ... recipe = zc.recipe.egg
    ... find-links = %(server)s
    ... index = %(server)s/index
    ... unzip = true
    ... """ % dict(server=link_server))

We also used the unzip uption to request a directory, rather than
a zip file.

    >>> print system(buildout),

Then we'll get a new demo egg:

    >>> ls(sample_buildout, 'eggs')
    -  demo-0.2-py2.3.egg
    d  demo-0.3-py2.3.egg
    d  demoneeded-1.0-py2.3.egg

Note that we removed the distribution option, and the distribution
defaulted to the part name.

The script is updated too:

    >>> print system(os.path.join(sample_buildout, 'bin', 'demo')),
    3 1

You can control which scripts get generated using the scripts option.
For example, to suppress scripts, use the scripts option without any
arguments:


    >>> write(sample_buildout, 'buildout.cfg',
    ... """
    ... [buildout]
    ... parts = demo
    ...
    ... [demo]
    ... recipe = zc.recipe.egg
    ... find-links = %(server)s
    ... index = %(server)s/index
    ... scripts =
    ... """ % dict(server=link_server))


    >>> print system(buildout),

    >>> ls(sample_buildout, 'bin')
    -  buildout

You can also control the name used for scripts:

    >>> write(sample_buildout, 'buildout.cfg',
    ... """
    ... [buildout]
    ... parts = demo
    ...
    ... [demo]
    ... recipe = zc.recipe.egg
    ... find-links = %(server)s
    ... index = %(server)s/index
    ... scripts = demo=foo
    ... """ % dict(server=link_server))

    >>> print system(buildout),

    >>> ls(sample_buildout, 'bin')
    -  buildout
    -  foo

