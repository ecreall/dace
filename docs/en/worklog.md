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
