In the ``ls`` testing method, add keyword argument ``lowercase_and_sort_output``.
The default is False, so no change.
When true, as the name says, it sorts the output by lowercase, and prints it lowercase.
We need this in one test because with ``setuptools`` 75.8.1 we no longer have a filename ``MIXEDCASE-0.5-pyN.N.egg``, but ``mixedcase-0.5-pyN.N.egg``.
[maurits]
