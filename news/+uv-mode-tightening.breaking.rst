The ``installer = uv`` mode tightens several legacy behaviors.
``find-links`` entries pointing at a Mercurial repository (``hg:`` or
``hg+``) or carrying ``#egg=``/``#md5=`` URL fragments now raise a clear
``UserError`` naming the entry, instead of surfacing uv's own parse error.
Offline mode (``buildout -o``) now forwards ``--offline`` to uv, so resolves
are served by uv's local cache alone and builds that relied on network
access during offline runs must warm the cache first.
The ``download-cache`` option is deprecated: uv keeps downloads in its own
cache and the download cache is not populated; setting the option logs a
deprecation warning, and the directory is still consulted as a find-links
location.  [gotcha]
