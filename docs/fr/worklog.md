# Fil de l'eau

Journal au fil de l'eau des travaux sur ce dépôt, du plus récent au plus ancien.
English version: [`../en/worklog.md`](../en/worklog.md).

## 2026-07-13

- Fork de `ecreall/dace` vers `michaellaunay/dace` ; reprise de la maintenance
  par Michaël Launay (Logikascium).
- Conversion de `README.rst` et `CHANGES.rst` en Markdown ; README réécrit avec
  le statut du dépôt et la feuille de route de modernisation.
- Mise à jour des métadonnées de build (`setup.py` : URLs du fork, champ
  mainteneur, description longue en Markdown) ; ajout d'un `pyproject.toml`
  minimal (PEP 518) ; mise à jour du `MANIFEST.in`.
- Ajout de `constraints-legacy.txt` (épinglages de dépendances 2017 connus pour
  fonctionner) et d'un workflow de CI legacy best-effort (`python:3.6-buster`).
- Mise en place de la structure de documentation bilingue (`docs/en`,
  `docs/fr`) et de ce fil de l'eau.
- Exclusion des artefacts de livraison (`*.patch`, `*.diff`, archives) et des
  résidus de `git apply` via `.gitignore` ; suppression de
  `dace-docs-structure.patch`, commité par erreur.
- Analyse du premier run de CI : les sdists de 2016/2017 (`zope.interface`
  4.3.3, même motif dans BTrees/persistent) ne se construisent plus avec un
  setuptools moderne — l'API `Feature` qu'ils importent a été supprimée dans
  setuptools 46 — d'où l'échec de résolution de pip. Le workflow installe
  désormais `setuptools<46` en premier.
- Durcissement du workflow pour Debian buster archivée (apt repointé vers
  archive.debian.org) et ajout de `libzmq3-dev`, nécessaire pour compiler
  pyzmq 14.4.1 (aucun wheel Python 3.6 n'existe), comme dans les prérequis
  historiques ; `actions/checkout` passé en v5 (dépréciation Node 20).
- Deuxième run de CI : l'installation des dépendances est au vert et la suite
  historique est vivante — 88 tests collectés, mais 88 erreurs sur un module
  `mock` manquant. dace ne l'importe jamais lui-même : le scan venusian de
  substanced (déclenché par `dace/testing.py` à la création du Configurator)
  importe les modules de test de substanced, qui font `import mock` — la
  raison exacte pour laquelle nova-ideo embarquait historiquement `mock` dans
  ses requires. Corrigé par un extra `[test]` (`mock`, épinglé en 2.0.0) que
  le workflow installe désormais.
