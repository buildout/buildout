.. This text is adapted from https://github.com/plone/plone.releaser/blob/master/ADD-A-NEWS-ITEM.rst


For contributors
----------------

The ``CHANGES.rst`` file is managed using `towncrier <https://pypi.org/project/towncrier/>`_.
All non trivial changes must be accompanied by an entry in the ``news`` directory.
Using such a tool instead of editing the file directly, has the following benefits:

- It avoids merge conflicts in ``CHANGES.rst``.
- It avoids news entries ending up under the wrong version header.

The best way of adding news entries is this:

- First create an issue describing the change you want to make.
  The issue number serves as a unique indicator for the news entry.
  As example, let's say you have created issue 42.

- Create a file inside of the ``news/`` directory, named after that issue number:

  - For bug fixes: ``42.bugfix``.
  - For new features: ``42.feature``.
  - For breaking changes: ``42.breaking``.
  - For development issues: ``42.develop``.
  - Any other extensions are ignored.

- The contents of this file should be reStructuredText formatted text that will be used as the content of the ``CHANGES.rst`` entry.
  Note: all lines are joined together, so do not use formatting that requires multiple lines.

- Towncrier will automatically add a reference to the issue when rendering the ``CHANGES.rst`` file.

- If unsure, you can let towncrier do a dry run::

    towncrier --version=X --draft
