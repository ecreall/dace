# Worklog

Running log of the work on this repository, newest first.
Version française : [`../fr/worklog.md`](../fr/worklog.md).

## 2026-07-13

- Forked `ecreall/dace` to `michaellaunay/dace`; maintenance resumed by
  Michaël Launay (Logikascium).
- Converted `README.rst` and `CHANGES.rst` to Markdown; rewrote the README
  with the repository status and the modernisation roadmap.
- Updated build metadata (`setup.py`: fork URLs, maintainer field, Markdown
  long description); added a minimal PEP 518 `pyproject.toml`; updated
  `MANIFEST.in`.
- Added `constraints-legacy.txt` (known-good 2017 dependency pins) and a
  best-effort legacy CI workflow (`python:3.6-buster`).
- Established the bilingual documentation structure (`docs/en`, `docs/fr`)
  and this worklog.
- Ignored delivery artifacts (`*.patch`, `*.diff`, archives) and `git apply`
  leftovers in `.gitignore`; removed `dace-docs-structure.patch`, committed
  by mistake.
- Analysed the first CI run: the 2016/2017 sdists (`zope.interface` 4.3.3,
  and the same pattern in BTrees/persistent) no longer build with modern
  setuptools — the `Feature` API they import was removed in setuptools 46 —
  which made pip's resolution impossible. The workflow now installs
  `setuptools<46` first.
- Hardened the workflow for the archived Debian buster (apt repointed to
  archive.debian.org) and added `libzmq3-dev`, required to compile
  pyzmq 14.4.1 (no Python 3.6 wheel exists) as in the historical
  prerequisites; bumped `actions/checkout` to v5 (Node 20 deprecation).
- Second CI run: the dependency installation is now green and the historical
  suite is alive — 88 tests collected, but all 88 error on a missing `mock`
  module. dace itself never imports it: substanced's venusian scan (triggered
  by `dace/testing.py` at Configurator setup) imports substanced's own test
  modules, which `import mock` — the very reason nova-ideo historically
  shipped `mock` in its requires. Fixed by adding a `[test]` extra
  (`mock`, pinned at 2.0.0) that the workflow now installs.
