---
date: 2025-11-06T14:35:12+01:00
researcher: Godefroid Chapelle
git_commit: a1c67f8d65bdd6d2eb7f0fdb29fef11b6c0eb9ed
branch: ""
repository: buildout
topic: "how is pkg_resources.WorkingSet used?"
tags: [research, codebase, pkg_resources, workingset, buildout, easy_install, patches, caching]
status: complete
last_updated: 2025-11-06
last_updated_by: Godefroid Chapelle
---

# Research: How is pkg_resources.WorkingSet Used?

**Date**: 2025-11-06T14:35:12+01:00
**Researcher**: Godefroid Chapelle
**Git Commit**: a1c67f8d65bdd6d2eb7f0fdb29fef11b6c0eb9ed
**Branch**: (detached HEAD)
**Repository**: buildout

## Research Question
How is `pkg_resources.WorkingSet` used in the buildout repository?

## Summary
`pkg_resources.WorkingSet` is a fundamental component of buildout's dependency management system. WorkingSet instances are used to track collections of installed Python distributions, resolve dependencies, and determine which packages are active in the Python environment. The buildout codebase extensively uses both custom WorkingSet instances (created for specific operations) and the global `pkg_resources.working_set` singleton. Key usage patterns include custom dependency resolution that extends standard pkg_resources behavior, automatic setuptools addition for namespace packages, version constraint application from buildout's [versions] section, WorkingSet patching for compatibility with various setuptools versions, and WorkingSet caching for performance optimization.

## Detailed Findings

### WorkingSet Core Usage Locations

#### Primary Implementation Files
- **`src/zc/buildout/easy_install.py`** - Main WorkingSet operations including creation, dependency resolution, and sorting
  - Line 89: Gets initial paths from global `pkg_resources.working_set`
  - Line 815: Creates empty WorkingSet for installations
  - Lines 826-912: Custom dependency resolution logic modifying `pkg_resources.WorkingSet.resolve()` behavior
  - Line 2421: Returns sorted WorkingSet from `sort_working_set()` function

- **`src/zc/buildout/buildout.py`** - WorkingSet usage for buildout operations
  - Line 668: Creates WorkingSet from entries during bootstrap
  - Line 669: Requires zc.buildout in working set
  - Lines 410-426: Version pinning using global working set
  - Lines 1286, 1492: Passes global working set for extension and recipe loading

- **`src/zc/buildout/patches.py`** - Patches WorkingSet.find() method
  - Lines 319-403: `patch_pkg_resources_working_set_find()` function
  - Line 400: Applies patched find method to WorkingSet class

- **`zc.recipe.egg_/src/zc/recipe/egg/egg.py`** - WorkingSet caching implementation
  - Line 29: Defines cache attribute name
  - Lines 96-149: `_working_set()` method with caching logic
  - Line 149: Returns deep copy to prevent mutation

### WorkingSet Creation Patterns

#### Empty WorkingSet Creation
```python
# src/zc/buildout/easy_install.py:815
if working_set is None:
    ws = pkg_resources.WorkingSet([])
else:
    ws = working_set
```
Used when no existing working set is provided to `Installer.install()`.

#### WorkingSet from Entry Paths
```python
# src/zc/buildout/buildout.py:668
ws = pkg_resources.WorkingSet(entries)
ws.require('zc.buildout')
```
Creates WorkingSet from list of file system paths during bootstrap.

#### WorkingSet from Sorted Paths
```python
# src/zc/buildout/easy_install.py:2421
return pkg_resources.WorkingSet(sorted_paths)
```
Returns new WorkingSet with paths sorted by priority (develop → eggs → other).

### WorkingSet Methods and Operations

#### The `find()` Method
Used extensively to check if requirements are satisfied:
- `easy_install.py:780`: Checks before fetching distributions
- `buildout.py:411-420`: Finds zc.buildout with fallback to different spellings
- `buildout.py:1190-1195`: Searches with canonicalized names
- `buildout.py:1470`: Checks if recipe already loaded
- `easy_install.py:1396-1416`: Finds distributions for script generation

#### The `add()` Method
Adds distributions to working sets:
- `easy_install.py:707-708`: `ws.add(_d, replace=True)` after compilation
- `easy_install.py:721-722`: `ws.add(dist)` for simple addition

#### The `require()` Method
- `buildout.py:669`: `ws.require('zc.buildout')` ensures buildout and dependencies are activated

#### The `resolve()` Method
- `buildout.py:1035`: Resolves recipe requirements for signature computation

#### Direct Iteration
```python
# easy_install.py:1005-1013
ws = list(ws)
ws.sort()
for dist in ws:
    if req in dist.requires():
        # process distribution
```

#### Accessing Attributes
- `ws.entries` (line 836): Gets list of paths in working set
- `dist.location` (lines 89, 1369, 2413): Extracts distribution locations
- `dist.key`, `dist.project_name`, `dist.version`: Various distribution attributes

### Custom Dependency Resolution Implementation

Buildout implements custom dependency resolution (`easy_install.py:824-912`) that extends standard `pkg_resources.WorkingSet.resolve()`:

#### Why Custom Resolution?
Comment at lines 825-829 explains:
> "This is code modified from pkg_resources.WorkingSet.resolve. We can't reuse that code directly because we have to constrain our requirements"

#### Key Differences from Standard Resolution

1. **Version Constraint Application**
   - Applies `[versions]` section constraints via `_constrain()` method
   - Standard resolution uses requirements as-is from dependencies

2. **Custom Environment Usage**
   - Creates separate `Environment` from WorkingSet entries (line 836)
   - Uses `Environment.best_match()` instead of WorkingSet methods

3. **Buildout-Specific Conflict Handling** (lines 849-861)
   - Allows version conflicts during buildout runs (installing buildout/recipes)
   - Strict checking only for non-buildout installations

4. **Automatic setuptools Addition** (line 869)
   - Detects namespace packages needing pkg_resources
   - Automatically adds setuptools requirement

5. **Requirement Logging** (line 867)
   - Tracks which distributions require each dependency
   - Custom feature for debugging and version reporting

6. **Extras Validation** (lines 878-903)
   - Validates requested extras exist
   - Can optionally allow unknown extras

### WorkingSet Patching

The `patch_pkg_resources_working_set_find()` function (`patches.py:319-403`) patches the WorkingSet.find() method to handle naming inconsistencies:

#### When Applied
- Only patches setuptools versions >= 62.0.0 and < 75.8.2
- Versions < 62 lack required `normalized_to_canonical_keys` attribute
- Versions >= 75.8.2 already have the fix

#### Patched Behavior
The patched find() method tries multiple name spellings:
```python
candidates = (
    req.key,
    self.normalized_to_canonical_keys.get(req.key),
    safe_name(req.key).replace(".", "-"),
)
```
This handles variations like "zope.interface", "zope-interface", "zope_interface".

### WorkingSet Caching Implementation

The `zc.recipe.egg` implements sophisticated WorkingSet caching:

#### Cache Storage
- Stored as attribute on buildout object: `_zc_recipe_egg_working_set_cache`
- Shared across all recipe instances in same buildout

#### Cache Key Composition
Composite key from all parameters affecting working set:
```python
cache_key = (
    tuple(distributions),
    eggs_dir,
    develop_eggs_dir,
    offline,
    newest,
    tuple(links),
    index,
    tuple(allow_hosts),
    allow_unknown_extras,
)
```

#### Mutability Protection
Returns deep copy to prevent cache corruption:
```python
# egg.py:149
return copy.deepcopy(cache_storage[cache_key])
```

### Global vs Local WorkingSets

The codebase distinguishes between:

1. **Global `pkg_resources.working_set`**
   - Singleton representing system Python environment
   - Modified when installing extensions and recipes
   - Used for version detection and initial path setup

2. **Local WorkingSet instances**
   - Created for specific operations
   - Isolated from global environment
   - Used for dependency resolution and script generation

### WorkingSet Sorting

The `sort_working_set()` function (`easy_install.py:2399-2421`) ensures proper priority:
1. Develop eggs (highest priority)
2. Regular eggs from eggs directory
3. Other paths (system packages, etc.)

This ensures develop eggs always take precedence during development.

## Code References

### Core Implementation
- `src/zc/buildout/easy_install.py:89` - Initial path extraction from global working set
- `src/zc/buildout/easy_install.py:815` - Empty WorkingSet creation
- `src/zc/buildout/easy_install.py:826-912` - Custom dependency resolution
- `src/zc/buildout/easy_install.py:2399-2421` - WorkingSet sorting function
- `src/zc/buildout/buildout.py:668-669` - Bootstrap WorkingSet creation
- `src/zc/buildout/buildout.py:410-426` - Version pinning logic

### Patching
- `src/zc/buildout/patches.py:319-403` - WorkingSet.find() patch
- `src/zc/buildout/patches.py:279-316` - Requirement.__contains__() patch

### Caching
- `zc.recipe.egg_/src/zc/recipe/egg/egg.py:96-149` - Caching implementation
- `zc.recipe.egg_/src/zc/recipe/egg/egg.py:151-167` - Cache storage

### Documentation
- `zc.recipe.egg_/src/zc/recipe/egg/working_set_caching.rst` - Caching documentation
- `README.rst:64-112` - Namespace package handling context

## Architecture Documentation

### Dependency Resolution Architecture
Buildout's dependency resolution extends pkg_resources with:
- Version constraints from `[versions]` section
- Automatic setuptools addition for namespace packages
- Custom conflict handling for buildout operations
- Requirement tracking for debugging

### Caching Architecture
WorkingSet caching improves performance by:
- Avoiding repeated dependency resolution
- Preventing redundant downloads
- Sharing cached working sets across multiple buildout parts
- Using deep copies to prevent cache corruption

### Patching Architecture
Monkey patches address compatibility issues:
- WorkingSet.find() patch handles name spelling variations
- Requirement.__contains__() patch enables normalized name comparison
- Version-based conditional patching ensures compatibility

### Priority Architecture
WorkingSet sorting ensures correct distribution priority:
- Develop eggs override installed eggs
- Eggs directory takes precedence over system packages
- Consistent ordering across buildout operations

## Related Research
- Version management and constraint application in buildout
- Namespace package handling evolution (pkg_resources → native)
- setuptools compatibility across versions

## Open Questions
1. Migration path from pkg_resources to importlib.metadata (setuptools deprecation in 2025)
2. Performance impact of deep copying WorkingSets in cache implementation
3. Interaction between patched WorkingSet.find() and custom Environment.best_match()
4. Edge cases in name normalization across different setuptools versions