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


## 2026-07-14

- Removed the dead upstream `cryptacular` C dependency from the CI
  environment (it was never pinned: pip was silently building the 1.6.2
  sdist). The maintained drop-in rewrite (`michaellaunay/cryptacular` 2.x,
  PyCA bcrypt + hashlib backends, hash-compatible with the deployed module)
  is installed from its repository instead; `bcrypt`, `cffi` and `pycparser`
  pinned for the Python 3.6 target.


## 2026-07-15

- Opened the Phase 2 documentation of the engine (tranche 1):
  design document `architecture.md` (EN/FR — layers, metamodel and runtime
  class diagrams in mermaid, action-discovery sequence, reactor data flow,
  relations/roles, evolution, the three monkey-patches) and
  `usage-scenarios.md` (EN/FR — nine scenarios from Pyramid wiring to
  live-site definition evolution; the process example mirrors the engine's
  own test suite).
- Docstring pass on the orientation-critical modules: `patches.py` (the
  three patches are now self-documented), `__init__.py` (evolve steps),
  `system.py`, `subscribers.py`, `descriptors/__init__.py`, and package
  docstrings for the three empty sub-package `__init__` files.
- Added `tools/doc_coverage.py` (stdlib `ast`, runs on 3.6 and 3.12).
  Coverage: 7.8 % → 9.2 % (60 modules, 180 classes, 727 functions to
  cover). The metric paces the next tranches: 2 = `processinstance/`,
  3 = `processdefinition/` + `descriptors/` + `relations/`,
  4 = `objectofcollaboration/` + `catalog/` + `util.py`.


- Tranche 2 of the docstring pass: the whole runtime
  (`dace/processinstance/`) — 224 docstrings inserted with an AST-based,
  decorator-aware tool, written from a full read of the seven modules
  (node lifecycle, decisions and their sibling-cancellation, business
  actions and the four-guard pipeline, events/kinds and the after-commit
  arming, virtual start work-items, gateways, cooperative locking,
  runtime transitions). Coverage: 9.2 % → 32.4 % (processinstance:
  9/9 modules, 60/63 classes, 175/321 functions). Known residue, left
  for the review pass: the ~45 near-duplicate `ExecutionContext`
  accessors (documented at class level by their naming grid) and a
  handful of small helpers. Next: tranche 3 = `processdefinition/` +
  `descriptors/` + `relations/`.


- Tranche 3 of the docstring pass: the declarative metamodel
  (`dace/processdefinition/`), the relation descriptors
  (`dace/descriptors/`) and the oid-level relation catalog
  (`dace/relations/`) — 177 docstrings from a full read of the twenty
  modules. Highlights fixed in writing: the `Transaction`/`Path`
  path-algebra (types, recursive path collection, lazy topology and its
  `_dirty` invalidation), the graph normalisation and its synthetic
  nodes (`startpg`, `endeg`, `mergepg`, `mergeeg` — the names daceui
  displays), the definition-side startable-path exploration behind
  virtual start work-items, the four descriptors' re-parenting and
  `__property__` bookkeeping, the defensive `ResourceRef` (zeopack
  ghosts), and the role of `relations/` as the storage of role grants
  (`reftype` always 'Role'). Coverage: 32.4 % → 50.7 %
  (processdefinition 24/24 classes, descriptors 6/6, relations 17/17).
  Residue: constructors, `__repr__`s and a handful of small helpers.
  Next: tranche 4 = `objectofcollaboration/` + `catalog/` + root
  modules (`util.py` chiefly).


- Tranche 4 — the last — of the docstring pass: the collaboration layer
  (`dace/objectofcollaboration/`), the 'dace' catalog (`dace/catalog/`)
  and the root modules (`util.py` chiefly, plus `wosystem.py`,
  `testing.py`, `interfaces.py`, `i18n/`) — 164 docstrings from a full
  read. Fixed in writing: the Job/EventJob re-establishment and
  oid-based argument passing, the reactor command socket
  (tcp://127.0.0.1:12345), the role-grant model (Role relations with a
  root mirror, superior hierarchy, access keys
  `'<role>_<oid>'`), the startup synchronisation of process definitions
  and the `node_definition` rewiring that makes the restart mandatory,
  the system crawler's new-transactions gate, and the two adapter
  contracts behind the 18 catalog indexes.
- **Phase-2 docstring pass closed**: 7.8 % → 67.6 % overall — 60/60
  modules, 163/180 classes, 432/727 functions. The uncovered residue is
  deliberate policy: constructors, `__repr__`, interface method stubs,
  and the near-duplicate accessor grids (ExecutionContext, the five
  catalog search adapters) documented at class level. Next candidates
  for the documentation effort: human review of the four tranches, and
  the BPMN→mermaid extractor over the host applications' 24 process
  packages.
