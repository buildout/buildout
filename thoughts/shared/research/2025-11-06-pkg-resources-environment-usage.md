---
date: 2025-11-06T15:37:04+01:00
researcher: Godefroid Chapelle
git_commit: b2cb9f1e8d84431a1023362f3ff98b4a5addad0d
branch: analyze-pkgresources
repository: buildout
topic: "How is pkg_resources.Environment being used?"
tags: [research, codebase, pkg_resources, environment, buildout, easy_install, platform-compatibility, dependency-resolution]
status: complete
last_updated: 2025-11-06
last_updated_by: Godefroid Chapelle
---

# Research: How is pkg_resources.Environment Being Used?

**Date**: 2025-11-06T15:37:04+01:00
**Researcher**: Godefroid Chapelle
**Git Commit**: b2cb9f1e8d84431a1023362f3ff98b4a5addad0d
**Branch**: analyze-pkgresources
**Repository**: buildout

## Research Question
How is `pkg_resources.Environment` being used in the buildout repository?

## Summary
`pkg_resources.Environment` is extensively customized and used throughout buildout for distribution discovery, version resolution, and platform compatibility handling. Buildout defines a custom `Environment` class that extends `pkg_resources.Environment` with two major enhancements: (1) canonicalized package name handling via `EnvironmentMixin` to address setuptools 69.3+ naming inconsistencies, and (2) relaxed macOS platform compatibility that accepts distributions when architecture matches, regardless of macOS version differences. The Environment is used differently from WorkingSet - Environment represents available distributions across paths (for discovery and selection), while WorkingSet represents activated distributions (for runtime path management). During dependency resolution, buildout creates a fresh Environment from WorkingSet entries to find best-matching distributions, apply version constraints from `[versions]` section, and handle version conflicts with custom logic.

## Detailed Findings

### Custom Environment Class Implementation

#### Class Hierarchy
Buildout defines two related classes:

**EnvironmentMixin** (`src/zc/buildout/easy_install.py:98-130`)
- Mixin class providing canonicalized name handling
- Used by both `Environment` and `AllowHostsPackageIndex`
- Addresses setuptools 69.3+ issue where distributions get different names (GitHub #647)
- Overrides `__getitem__()` to use `normalize_name()` for lookups
- Overrides `add()` to store distributions under normalized keys

**Environment** (`src/zc/buildout/easy_install.py:132-223`)
```python
class Environment(EnvironmentMixin, pkg_resources.Environment):
```
- Inherits from both `EnvironmentMixin` and `pkg_resources.Environment`
- Adds `_mac_machine_type` cached property for architecture detection
- Overrides `can_add()` for macOS platform compatibility

#### Overridden Methods

**`__getitem__(project_name)`** (lines 109-118)
- Returns newest-to-oldest list of distributions for a project
- Normalizes project name before lookup: `distribution_key = normalize_name(project_name)`
- Returns empty list if project not found
- Enables case-insensitive, spelling-variation-tolerant lookups

**`add(dist)`** (lines 120-129)
- Adds distribution if `can_add()` returns True and distribution has version
- Normalizes `dist.key` before storing: `distribution_key = normalize_name(dist.key)`
- Maintains distributions sorted by `hashcmp` attribute (newest first)
- Prevents duplicate additions

**`can_add(dist)`** (lines 184-223)
- First tries parent class implementation
- If parent returns False and platform is macOS, applies custom logic
- Validates Python version compatibility
- Extracts architecture from distribution platform string
- Accepts distribution if architecture matches, ignoring macOS version numbers
- Logs debug message when accepting despite platform mismatch

### Environment Creation Patterns

#### Pattern 1: Installer Environment
**Location**: `src/zc/buildout/easy_install.py:413-419`
```python
def _make_env(self):
    full_path = self._get_dest_dist_paths() + self._path
    env = Environment(full_path)
    self._eggify_env_dest_dists(env, self._dest)
    return env
```
- Called during `Installer.__init__()` (line 405)
- Combines destination paths with additional search paths
- Post-processes to set `EGG_DIST` precedence for destination distributions
- Stored as `self._env` for installer instance

#### Pattern 2: Resolution Environment
**Location**: `src/zc/buildout/easy_install.py:836`
```python
env = Environment(ws.entries)
```
- Creates fresh Environment from WorkingSet entries
- Used exclusively in dependency resolution loop
- Comment explains: "We want to look for new eggs unless what we have is the best that matches the requirement"
- Recreated on every `install()` call

#### Pattern 3: Verification Environment
**Location**: `src/zc/buildout/easy_install.py:2171`
```python
env = Environment([location])
```
- Creates Environment with single location
- Used to verify a specific distribution is present
- Extracts and validates distribution metadata

#### Pattern 4: Temporary Environment
**Location**: `src/zc/buildout/easy_install.py:555`
```python
env = Environment(paths)
```
- Created from pip install results
- Validates that pip successfully installed distributions
- Iterates over projects to collect all installed distributions

### Environment Methods and Operations

#### `best_match(requirement, working_set)`
Used to find the best distribution matching a requirement:

**Post-installation verification** (line 715):
```python
dist = self._env.best_match(requirement, ws)
```
- Called after fetching and installing a distribution
- Verifies newly installed distribution is discoverable

**Dependency resolution** (line 848):
```python
try:
    dist = env.best_match(req, ws)
except pkg_resources.VersionConflict as err:
    # Handle conflicts...
```
- May raise `pkg_resources.VersionConflict`
- Different handling for buildout run vs normal installation
- Returns None if no match found

#### `scan(paths)`
Used to rescan paths for new distributions:

**Location**: `src/zc/buildout/easy_install.py:422`
```python
self._env.scan(self._get_dest_dist_paths())
```
- Called in `_env_rescan_dest()` method
- Updates environment after new distributions added
- Followed by precedence post-processing

#### `__getitem__(project_name)` (Indexing)
Used extensively for distribution lookup:

**In `_satisfied()` method** (line 463):
```python
dists = [dist for dist in self._env[req.project_name] if dist in req]
```
- Returns sorted list (newest first)
- Filters to requirement-satisfying distributions

**In `_obtain()` method** (line 600):
```python
dists = [dist for dist in index[requirement.project_name] if ...]
```
- Used on `AllowHostsPackageIndex` (also uses `EnvironmentMixin`)
- Gets available distributions from package index

**In `_eggify_env_dest_dists()` method** (line 440):
```python
for project_name in env:
    for dist in env[project_name]:
        # Set precedence...
```
- Iterates all projects in environment
- Modifies distribution precedence

### macOS Platform Compatibility

#### The Problem
Documented in docstring (lines 143-169):
- `pkg_resources.get_platform()` returns platform where Python was built (e.g., "macosx-11.0-arm64")
- `pkg_resources.get_supported_platform()` returns current OS version (e.g., "macosx-15.4-arm64")
- When buildout converts wheels to eggs, egg name uses `get_supported_platform()`
- Standard `pkg_resources.compatible_platforms()` rejects eggs with version mismatch
- Result: Eggs created by current Python are rejected despite being compatible

#### The Solution
Custom `can_add()` implementation (lines 184-223):

1. **Try parent implementation first** (line 194):
   ```python
   if super().can_add(dist):
       return True
   ```

2. **Check if macOS** (line 196):
   ```python
   if sys.platform != "darwin":
       return False
   ```

3. **Validate Python version** (lines 202-207):
   ```python
   py_compat = (
       self.python is None
       or dist.py_version is None
       or dist.py_version == self.python
   )
   ```

4. **Parse and compare architectures** (lines 209-215):
   ```python
   provMac = macosVersionString.match(dist.platform)
   if not provMac:
       return False
   provided_machine_type = provMac.group(3)
   if provided_machine_type != self._mac_machine_type:
       return False
   ```

5. **Accept and log** (lines 216-223):
   ```python
   logger.debug(
       "Accepted dist %s although its provided platform %s does not "
       "match our supported platform %s.",
       dist, dist.platform, self.platform,
   )
   return True
   ```

#### Machine Type Extraction
**Cached property** (`_mac_machine_type`, lines 171-182):
```python
@cached_property
def _mac_machine_type(self):
    match = macosVersionString.match(self.platform)
    if match is None:
        return ""
    return match.group(3)
```
- Extracts architecture from platform string like "macosx-15.4-arm64"
- Returns "arm64" or "x86_64"
- Returns empty string for non-Mac platforms
- Cached for performance

### Environment in Dependency Resolution

#### Why Environment Instead of WorkingSet
Comment at lines 826-829 explains:
> "This is code modified from pkg_resources.WorkingSet.resolve. We can't reuse that code directly because we have to constrain our requirements"

**Key differences:**

1. **Search Scope**
   - `WorkingSet.find()`: Only searches activated distributions
   - `Environment`: Searches all distributions at specified paths
   - Enables discovering distributions not yet in WorkingSet

2. **Version Constraints**
   - Standard `WorkingSet.resolve()`: No constraint mechanism
   - Buildout: Applies `[versions]` constraints via `_constrain()` before every lookup
   - Custom loop allows constraining each requirement individually

3. **Conflict Handling**
   - Standard: Strict version conflict detection
   - Buildout: Allows conflicts during buildout/recipe installation
   - Different behavior for `for_buildout_run=True` vs False

#### Resolution Flow

**Phase 1: Setup** (lines 814-836)
```python
if working_set is None:
    ws = pkg_resources.WorkingSet([])
else:
    ws = working_set

requirements = [
    self._constrain(requirement)
    for requirement in requirements
    if not requirement.marker or requirement.marker.evaluate()
]

env = Environment(ws.entries)
```
- Create or reuse WorkingSet
- Constrain all initial requirements
- Create Environment from WorkingSet entries

**Phase 2: Resolution Loop** (lines 838-912)
```python
while requirements:
    current_requirement = requirements.pop(0)
    req = self._constrain(current_requirement)

    dist = best.get(req.key)
    if dist is None:
        try:
            dist = env.best_match(req, ws)
        except pkg_resources.VersionConflict as err:
            if not for_buildout_run:
                raise VersionConflict(err, ws)

    if dist is None:
        for dist in self._get_dist(req, ws):
            self._maybe_add_setuptools(ws, dist)

    best[req.key] = dist
    extra_requirements = dist.requires(req.extras)[::-1]
    requirements.extend(extra_requirements)
    processed[req] = True
```

**Key steps:**
1. Constrain requirement with `[versions]` section
2. Check if already resolved in `best` dictionary
3. Try finding in Environment with `best_match()`
4. If not found, download/install via `_get_dist()`
5. Record in `best` and queue dependencies
6. Continue breadth-first until all dependencies resolved

#### Version Conflict Detection

**Via best_match()** (lines 848-861):
```python
try:
    dist = env.best_match(req, ws)
except pkg_resources.VersionConflict as err:
    logger.debug("Version conflict...")
    if not for_buildout_run:
        raise VersionConflict(err, ws)
```
- `best_match()` raises `VersionConflict` if conflict detected
- Buildout run allows conflicts (system packages may conflict)
- Normal installation immediately raises exception

**Manual validation** (lines 870-874):
```python
if dist not in req:
    logger.info(self._version_conflict_information(req.key))
    raise VersionConflict(
        pkg_resources.VersionConflict(dist, req), ws)
```
- Checks if previously-resolved distribution satisfies new requirement
- Provides detailed conflict information via `_version_conflict_information()`
- Includes `[versions]` constraints and requirement chain

#### Constraint Application

**The `_constrain()` method** (lines 783-795):
```python
def _constrain(self, requirement):
    canonical_name = canonicalize_name(requirement.project_name)
    constraint = self._versions.get(canonical_name)
    if constraint:
        requirement = _constrained_requirement(constraint, requirement)
    return requirement
```

**Used at:**
- Line 808-812: Initial requirements constraining
- Line 841: Every requirement in resolution loop

**Constraint types:**
- Exact version: `package = 1.2.3` → `package==1.2.3`
- Range constraints: `package = <2.0` or `package = >=1.0,<2.0`

**Integration with Environment:**
- Constraints applied BEFORE passing to `env.best_match()`
- Environment sees already-constrained requirements
- Ensures `[versions]` section honored throughout resolution

### Distribution Retrieval from Environment

#### Query in `_satisfied()` (lines 463-546)
```python
dists = [dist for dist in self._env[req.project_name] if dist in req]

if not dists:
    return None, self._obtain(req, source)

for dist in dists:
    if (dist.precedence == pkg_resources.DEVELOP_DIST):
        return dist, None

# Check exact pins, prefer_final, newest mode...
```

**Decision factors:**
1. **Develop eggs**: Always preferred
2. **Exact pins**: Use immediately, no index check
3. **Prefer final**: Filter pre-releases
4. **Newest mode**: Compare installed vs available

#### Obtaining from Index (lines 591-645)
```python
def _obtain(self, requirement, source=None):
    index = self._index
    if index.obtain(requirement) is None:
        return None

    dists = [dist for dist in index[requirement.project_name] if ...]

    # Filter final versions if preferred
    # Select highest version
    # Prefer download cache
```

**Index is AllowHostsPackageIndex**:
- Also uses `EnvironmentMixin`
- Provides canonicalized name handling
- Represents available packages from PyPI/find-links

#### Post-Install Verification (lines 714-716)
```python
self._env_rescan_dest()
dist = self._env.best_match(requirement, ws)
```
- Rescans destination after installation
- Verifies distribution is discoverable
- Uses installer's persistent `self._env`

### Environment vs WorkingSet Comparison

| Aspect | Environment | WorkingSet |
|--------|-------------|------------|
| **Purpose** | Distribution discovery and selection | Active distribution tracking |
| **Contents** | All available distributions at paths | Activated distributions |
| **Structure** | Dict mapping project names to dist lists | List of paths with by_key dict |
| **Usage** | Find best matches, check availability | Track what's active, resolve at runtime |
| **Creation** | `Environment(paths)` | `WorkingSet(paths)` |
| **Key Method** | `best_match(req, ws)` | `find(req)` |
| **Scope** | Broader - all possibilities | Narrower - current selection |

**Relationship:**
- Environment created FROM WorkingSet: `Environment(ws.entries)`
- Environment queries consider WorkingSet context: `best_match(req, ws)`
- WorkingSet updated AFTER Environment finds distribution: `ws.add(dist)`

### AllowHostsPackageIndex Integration

**Class definition** (`src/zc/buildout/easy_install.py:226-232`):
```python
class AllowHostsPackageIndex(EnvironmentMixin, _package_index.PackageIndex):
    pass
```

**Inheritance chain:**
- `AllowHostsPackageIndex` → `EnvironmentMixin` + `PackageIndex`
- `PackageIndex` → `pkg_resources.Environment` (in `_package_index.py:437`)

**Benefits:**
- Inherits canonicalized name handling from `EnvironmentMixin`
- Provides consistent lookup behavior with `Environment`
- Used in `_obtain()` for remote package discovery

**Usage** (line 406):
```python
self._index = self._get_index()
```
- Created during installer initialization
- Cached in `_indexes` dictionary
- Used to query PyPI/find-links for available packages

## Code References

### Core Implementation
- `src/zc/buildout/easy_install.py:98-130` - EnvironmentMixin class
- `src/zc/buildout/easy_install.py:132-223` - Custom Environment class
- `src/zc/buildout/easy_install.py:171-182` - `_mac_machine_type` property
- `src/zc/buildout/easy_install.py:184-223` - Custom `can_add()` method

### Environment Creation
- `src/zc/buildout/easy_install.py:413-419` - Installer environment creation
- `src/zc/buildout/easy_install.py:836` - Resolution environment creation
- `src/zc/buildout/easy_install.py:2171` - Verification environment creation
- `src/zc/buildout/easy_install.py:555` - Temporary environment creation

### Environment Operations
- `src/zc/buildout/easy_install.py:715` - Post-install best_match()
- `src/zc/buildout/easy_install.py:848` - Resolution best_match()
- `src/zc/buildout/easy_install.py:422` - Environment rescanning
- `src/zc/buildout/easy_install.py:463` - Distribution querying
- `src/zc/buildout/easy_install.py:600` - Index querying

### Dependency Resolution
- `src/zc/buildout/easy_install.py:824-912` - Custom resolution loop
- `src/zc/buildout/easy_install.py:783-795` - Constraint application
- `src/zc/buildout/easy_install.py:1847-1865` - Constraint logic
- `src/zc/buildout/easy_install.py:870-874` - Conflict detection

### Platform Compatibility
- `src/zc/buildout/easy_install.py:73` - macOS regex pattern
- `src/zc/buildout/easy_install.py:143-169` - Problem documentation
- `src/zc/buildout/easy_install.py:2149` - Reference in unpack_wheel()

### Related Classes
- `src/zc/buildout/easy_install.py:226-232` - AllowHostsPackageIndex
- `src/zc/buildout/_package_index.py:437` - PackageIndex base class

## Architecture Documentation

### Environment Extension Architecture
Buildout uses multiple inheritance to extend `pkg_resources.Environment`:
1. **EnvironmentMixin**: Provides canonicalized name handling
2. **Environment**: Adds macOS platform compatibility
3. **AllowHostsPackageIndex**: Combines both with PackageIndex

This architecture ensures consistent name normalization across all distribution lookups while maintaining compatibility with both local and remote package sources.

### Dependency Resolution Architecture
Buildout's custom resolution replaces `pkg_resources.WorkingSet.resolve()` with:
1. **Constraint Integration**: Applies `[versions]` section before every lookup
2. **Fresh Environment**: Creates new Environment from WorkingSet on each install
3. **Best Dictionary**: Tracks resolved distributions to prevent reprocessing
4. **Custom Conflict Handling**: Different behavior for buildout vs normal runs
5. **Breadth-First Processing**: Queues dependencies for systematic resolution

### Platform Compatibility Architecture
The macOS compatibility solution:
1. **Override Pattern**: Subclass with method override, not monkey patching
2. **Fallback Chain**: Try parent implementation first, then custom logic
3. **Platform-Specific**: Only activates on macOS via `sys.platform` check
4. **Cached Property**: Machine type extraction cached for performance
5. **Debug Logging**: Provides visibility into relaxed matching decisions

### Name Normalization Architecture
The EnvironmentMixin addresses setuptools 69.3+ naming changes:
1. **Mixin Pattern**: Shared behavior across Environment and PackageIndex
2. **Normalized Keys**: All storage uses `normalize_name()` keys
3. **Transparent Lookup**: Normalization automatic in `__getitem__()`
4. **Consistent Sorting**: Distributions sorted by hashcmp (newest first)

## Related Research
- `/Users/gotcha/co/buildout/thoughts/shared/research/2025-11-06-pkg-resources-workingset-usage.md` - WorkingSet usage and relationship with Environment

## Open Questions
1. Performance impact of creating fresh Environment on every install() call
2. Why is precedence manipulation needed via `_eggify_env_dest_dists()`?
3. Could the macOS compatibility logic be contributed back to pkg_resources?
4. Migration strategy when pkg_resources is removed from setuptools (end of 2025)
5. Are there edge cases where architecture matching alone is insufficient?