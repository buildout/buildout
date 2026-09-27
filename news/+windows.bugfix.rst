Windows fixes: a local package index spelled as a drive path
(``C:\index``) no longer reaches pip misread as a URL — drive paths are
converted to ``file://`` URIs like any other local index — and with
``installer = uv`` a ``file://`` index spelled as a native Windows path no
longer crashes resolution, while the fallback lookup for the uv executable
next to the Python interpreter now finds the ``uv.exe`` console script.
[gotcha]
