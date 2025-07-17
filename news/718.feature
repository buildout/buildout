When OS environment variable ``BUILDOUT_PIP_NO_BUILD_ISOLATION`` is set, call ``pip install`` with the ``no-build-isolation`` option.
This may be needed when installing packages that cannot be installed with the latest setuptools version.
See `issue 718 <https://github.com/buildout/buildout/issues/718>`_ for an explanation and alternative solutions.
Better is to use ``zc.buildout`` 4.1.12 or later, but that requires Python 3.9 or later.
Note that on Python 3.8 you may want to use at most ``setuptools`` 75.3.0, whether you use the new environment variable or not.
[maurits]
