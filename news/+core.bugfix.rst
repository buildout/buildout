Fixed spurious uninstall/reinstall cycles of parts whose recipe resolves
to a develop egg: a packaging run on the develop source tree regenerates
setuptools' ``SOURCES.txt``, which moved the directory hash, so
``_dir_hash`` now excludes it.
Offline mode (``buildout -o``) now reuses distributions that were
installed from wheels, whose dist-info layout was invisible to the offline
environment scan.
Fixed a ``TypeError`` that made zc.buildout unimportable on Python 3.9.
``query`` rejects malformed arguments (for example ``:port`` or
``a:b:c``) with a clear message stating the expected ``section:option``
format.
With ``installer = uv``, old-style wheels whose ``.dist-info`` directory
keeps the unescaped project name install correctly, and the uv floor is
0.12.11 because earlier 0.12.x served their own cache on ``--offline``
resolves.  [gotcha]
