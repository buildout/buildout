Repeated buildout runs are faster: sources listed in the ``develop``
option are no longer reinstalled (``pip install -e``) on every run.
An editable install is only redone when its ``setup.py``, ``setup.cfg``
or ``pyproject.toml`` is newer than its egg-link, when its egg-info is
missing, or when the develop-eggs directory changed; verbose output tells
the cases apart with ``Making editable install`` versus
``Keeping editable install of ...: its packaging metadata ... is
unchanged``.  [gotcha]
