# DaCE — data-centric workflow engine (`ecreall_dace`)

DaCE is a data-centric workflow engine for the [Pyramid](https://trypyramid.com) / [substanced](https://github.com/Pylons/substanced) / ZODB stack. It enables the definition and execution of complex business processes and the definition of objects of collaboration. In DaCE, rights management is based on the definition of roles.

## Repository status

This repository is a **maintained fork** of [`ecreall/dace`](https://github.com/ecreall/dace) (original development by Ecréall, 2014–2017), forked in July 2026 and maintained by Michaël Launay ([Logikascium](https://github.com/michaellaunay)). Ecréall's intellectual property was acquired by Logikascium in 2024; the license is unchanged: **AGPL v3+**.

This fork is part of the modernisation effort of the [Nova-Ideo](https://github.com/ecreall/nova-ideo) / [KuneAgi](https://github.com/ecreall/KuneAgi) participatory-innovation platform. The `master` branch currently reflects the **legacy state** of the engine (Python 3.6 era); see the [roadmap](#roadmap--planned-updates) below and `CHANGES.md` for what comes next.

## Features

- Process definitions with Activity, Exclusive Gateway, Parallel Gateway, and Events (StartEvent, IntermediateThrowEvent, IntermediateCatchEvent) of the following kinds: Terminate, Timer, Signal, Conditional
- Process instances indexed in ZODB with the substanced catalog, based on [hypatia](https://github.com/Pylons/hypatia) indexes
- An event loop built on tornado and zmq handles conditional and timer events *(legacy — scheduled for replacement by `asyncio`, see roadmap)*

## Current requirements (legacy)

- Python 3.6 only — the modernisation targets Python 3.12
- Pyramid 1.9.x, substanced 1.0a1, ZODB 5.x, tornado < 4, pyzmq
- Known-good dependency pins are provided in [`constraints-legacy.txt`](constraints-legacy.txt), extracted from the historical nova-ideo `versions.cfg` (the last environment in which the whole stack was known to work together)

## Installation

Add `ecreall_dace` to `install_requires` in your `setup.py`, then edit `production.ini` in your Pyramid application:

```ini
pyramid.includes =
    ...
    dace
```

For an isolated legacy development environment:

```bash
python3.6 -m pip install -c constraints-legacy.txt -e .
```

## Running the tests

```bash
python setup.py test
```

A best-effort GitHub Actions workflow ([`.github/workflows/tests.yml`](.github/workflows/tests.yml)) runs the suite inside a `python:3.6-buster` container. It will be stabilised during Phase 1 of the roadmap (reproducible legacy build).

## Used by

- [nova-ideo](https://github.com/ecreall/nova-ideo) and its variant [KuneAgi](https://github.com/ecreall/KuneAgi)
- [l'agenda commun](https://github.com/ecreall/lagendacommun)

## Documentation

Documentation lives in [`docs/`](docs/):

- [`docs/en/`](docs/en/) — primary documentation, in English
- [`docs/fr/`](docs/fr/) — documentation in French

Audits, design documents and the worklog are maintained in both languages. See [`docs/README.md`](docs/README.md) for the documentation policy.

Design documents: [architecture](docs/en/architecture.md) · [usage scenarios](docs/en/usage-scenarios.md) (English originals; French mirrors under [`docs/fr/`](docs/fr/)).

## Roadmap — planned updates

The plan follows the Nova-Ideo modernisation audit (Logikascium, July 2026):

1. **Phase 1 — Reproducible legacy build ("golden master").** Frozen environment and green CI replaying the existing test suite: the non-regression baseline for everything below.
2. **Phase 2 — Exhaustive documentation.** Docstring pass over the whole package, documentation of the event-loop protocol and of every monkey-patch in `dace/patches.py`, BPMN/mermaid diagrams generated automatically from the declarative process definitions.
3. **Phase 3 — Modernisation (target: version 2.0.0).**
   - Port to Python 3.12; Pyramid 2.x; ZODB 6
   - Replace the tornado < 4 + pyzmq event loop with `asyncio`, behind the existing API
   - Move from the abandoned substanced 1.0a1 to a maintained, trimmed-down fork
   - Migrate tests to pytest; packaging to PEP 621 (`pyproject.toml`) with `uv`; ruff linting; gradual typing
   - Python module names (dotted paths) are **frozen** to preserve existing ZODB pickles

Versioning: `1.1.x` = legacy maintenance on this fork; `2.0.0` = the modernised engine.

Open study (no decision taken): in the longer term, a possible migration to an external BPMN engine (such as Operaton) will be evaluated — deferred until the documentation phase is complete.

## Translations

This product has been translated into: French.

## Contribute

- Issue tracker: <https://github.com/michaellaunay/dace/issues>
- Source code: <https://github.com/michaellaunay/dace>
- Historical upstream: <https://github.com/ecreall/dace>

## License

The project is licensed under the AGPL v3 or later (AGPLv3+). See [`LICENSE`](LICENSE).
