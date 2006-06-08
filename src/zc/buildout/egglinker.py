##############################################################################
#
# Copyright (c) 2005 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Egg linker -- Link eggs together to build applications

Egg linker is a script that generates startup scripts for eggs that
include an egg's working script in the generated script.

The egg linker module also exports helper functions of varous kinds to
assist in custom script generation.

$Id$
"""

# XXX needs doctest
# XXX need to deal with extras

import os
import sys

import pkg_resources

def distributions(reqs, eggss):
    env = pkg_resources.Environment(eggss)
    ws = pkg_resources.WorkingSet()
    reqs = [pkg_resources.Requirement.parse(r) for r in reqs]
    return ws.resolve(reqs, env=env)

def path(reqs, eggss):
    dists = distributions(reqs, eggss)
    return [dist.location for dist in dists]

def location(spec, eggss):
    env = pkg_resources.Environment(eggss)
    req = pkg_resources.Requirement.parse(spec)
    dist = env.best_match(req, pkg_resources.WorkingSet())
    return dist.location    

def scripts(reqs, dest, eggss, scripts=None):
    dists = distributions(reqs, eggss)
    reqs = [pkg_resources.Requirement.parse(r) for r in reqs]
    projects = [r.project_name for r in reqs]
    path = "',\n  '".join([dist.location for dist in dists])
    generated = []

    for dist in dists:
        if dist.project_name in projects:
            for name in pkg_resources.get_entry_map(dist, 'console_scripts'):
                if scripts is not None:
                    sname = scripts.get(name)
                    if sname is None:
                        continue
                else:
                    sname = name

                sname = os.path.join(dest, sname)
                generated.append(sname)
                _script(dist, 'console_scripts', name, path, sname)

            name = 'py_'+dist.project_name
            if scripts is not None:
                sname = scripts.get(name)
            else:
                sname = name

            if sname is not None:
                sname = os.path.join(dest, sname)
                generated.append(sname)
                _pyscript(path, sname)

    return generated

def _script(dist, group, name, path, dest):
    entry_point = dist.get_entry_info(group, name)
    open(dest, 'w').write(script_template % dict(
        python = sys.executable,
        path = path,
        project = dist.project_name,
        name = name,
        module_name = entry_point.module_name,
        attrs = entry_point.attrs,
        ))
    try:
        os.chmod(dest, 0755)
    except (AttributeError, os.error):
        pass

script_template = '''\
#!%(python)s

import sys
sys.path[0:0] = [
  '%(path)s'
  ]


module = __import__(%(module_name)r, globals(),globals(), ['__name__'])
attrs = %(attrs)r

entry = module
for attr in attrs:
    try:
        entry = getattr(entry, attr)
    except AttributeError:
        raise ImportError("%%r has no %%r attribute" %% (module, attrs))

if __name__ == '__main__':
    entry()
'''


def _pyscript(path, dest):
    open(dest, 'w').write(py_script_template % dict(
        python = sys.executable,
        path = path,
        ))
    try:
        os.chmod(dest,0755)
    except (AttributeError, os.error):
        pass

py_script_template = '''\
#!%(python)s -i

import sys
sys.path[0:0] = [
  '%(path)s'
  ]
'''

def main():
    import pdb; pdb.set_trace()
    
