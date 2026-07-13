# Changelog

## Unreleased

### Fork maintenance — 2026-07-13 (`michaellaunay/dace`)

- Repository forked from `ecreall/dace`; maintenance resumed by Michaël Launay (Logikascium). Ecréall's intellectual property was acquired by Logikascium in 2024; license unchanged (AGPL v3+).
- `README.rst` and `CHANGES.rst` converted to Markdown (`README.md`, `CHANGES.md`); README rewritten with repository status, legacy requirements and the modernisation roadmap.
- Build metadata updated: fork URLs, maintainer field, Markdown `long_description`; minimal `pyproject.toml` added (PEP 518 `[build-system]` only — metadata stays in `setup.py` until the Phase 3 packaging migration); `MANIFEST.in` updated for Markdown files.
- Added `constraints-legacy.txt` (known-good 2017 dependency pins extracted from nova-ideo's `versions.cfg`) and a best-effort GitHub Actions workflow running the test suite in a `python:3.6-buster` container (to be stabilised in Phase 1).
- Bilingual documentation structure added (`docs/en/`, `docs/fr/`), including the worklog / fil de l'eau and a documentation policy (`docs/README.md`); stray `dace-fork-maj.zip` removed from version control.
- `.gitignore` now excludes delivery artifacts (patches, diffs, archives) and `git apply` leftovers; stray `dace-docs-structure.patch` removed from version control.

### Planned (modernisation roadmap → 2.0.0)

- Phase 1: reproducible legacy build + green CI (golden master).
- Phase 2: exhaustive documentation (docstrings, event-loop protocol, `dace/patches.py`, auto-generated BPMN diagrams).
- Phase 3: Python 3.12, Pyramid 2.x, ZODB 6; tornado/pyzmq event loop replaced by `asyncio`; maintained substanced fork; pytest; PEP 621 packaging with `uv`; ruff; gradual typing. Module dotted names frozen to preserve ZODB pickles.

### Inherited unreleased changes (upstream `1.1.1.dev`, 2017)

- Add a `remove_unique_process_instances` evolve step.
- Add a `update_catalogs_evolve` evolve step to update catalogs and reindex new indexes programmatically.
- On SIGTERM, stop the system thread. It was already done for SIGINT but not on SIGTERM.
- Can now execute `process_definitions_evolve` via the `sd_evolve` script.
- Fix `ConflictError` at startup when using several workers.
- Fix tests with latest pyramid version.
- Add support for Python 3.6.

## 1.1.0 — 2017-02-25

- Add `user_groups` getter to `User` class, and now include roles from groups when checking if the user has a given role.

## 1.0.3 — 2017-01-06

- Auto evolve `TimeEvent` if the definition changed.
- Fix the end of a sub-process.
- Optimizations of path finding to get the workitems.

## 1.0.2 — 2016-09-15

- Fix an issue with automatic actions.

## 1.0.1 — 2016-08-18

- Include mo files in the release.

## 1.0 — 2016-06-28

- Initial version.
