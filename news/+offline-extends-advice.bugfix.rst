Made the offline-mode error for a configuration file that cannot be
downloaded actionable: it now advises setting ``extends-cache`` to a cache
directory in the root configuration and running buildout once in online
mode, after which the download is reused from the cache.  A configured
``extends-cache`` directory is now created on first use, as the
documentation always promised; previously even the first *online* run
failed with "to be used as a download cache doesn't exist" unless the
directory was created by hand.  [gotcha]
