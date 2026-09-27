Structural refactoring under a new complexity gate: ``make complexity``
(radon) fails when a function grows beyond the checked-in baseline or when
new code exceeds grade B.  The high-complexity cores of ``Buildout``
(initialization, install, develop, query, upgrade, ``main``) and of
``easy_install.Installer`` were decomposed into module-level helpers
pinned by unit tests, several functions dropping from cyclomatic
complexity 20–60 to grade A or B without behavior change.
The monolithic modules split into focused ones — ``cli``, ``configfiles``,
``configsetup``, ``parts``, ``annotations``, ``scripts``, ``develop``,
``install_backend`` and ``errors`` — with the original modules
re-exporting for compatibility, and the frame-local ``__doing__``
error-context mechanism was replaced by a portable context manager, with
unchanged ``While:`` error output.  [gotcha]
