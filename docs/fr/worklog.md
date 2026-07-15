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


## 2026-07-14

- Suppression de la dependance C amont `cryptacular` de l'environnement de
  CI (elle n'etait pas epinglee : pip compilait silencieusement le sdist
  1.6.2). La reecriture drop-in maintenue (`michaellaunay/cryptacular` 2.x,
  backends bcrypt PyCA + hashlib, compatible hash pour hash avec le module
  deploye) est installee depuis son depot a la place ; `bcrypt`, `cffi` et
  `pycparser` epingles pour la cible Python 3.6.


## 2026-07-15

- Ouverture de la documentation de phase 2 du moteur (tranche 1) :
  document de conception `architecture.md` (EN/FR — couches, diagrammes de
  classes du métamodèle et du runtime en mermaid, séquence de découverte
  des actions, flux du réacteur, relations/rôles, évolution, les trois
  monkey-patches) et `usage-scenarios.md` (EN/FR — neuf scénarios, du
  câblage Pyramid à l'évolution des définitions sur site en production ;
  l'exemple de processus reprend la suite de tests du moteur).
- Passe de docstrings sur les modules critiques pour l'orientation :
  `patches.py` (les trois patches sont désormais auto-documentés),
  `__init__.py` (étapes d'évolution), `system.py`, `subscribers.py`,
  `descriptors/__init__.py`, et docstrings de paquet pour les trois
  `__init__` vides des sous-paquets.
- Ajout de `tools/doc_coverage.py` (`ast` de la stdlib, tourne en 3.6 et
  3.12). Couverture : 7,8 % → 9,2 % (60 modules, 180 classes,
  727 fonctions à couvrir). La métrique rythme les tranches suivantes :
  2 = `processinstance/`, 3 = `processdefinition/` + `descriptors/` +
  `relations/`, 4 = `objectofcollaboration/` + `catalog/` + `util.py`.


- Tranche 2 de la passe de docstrings : tout le runtime
  (`dace/processinstance/`) — 224 docstrings insérés avec un outil AST
  conscient des décorateurs, rédigés après lecture intégrale des sept
  modules (cycle de vie des nœuds, décisions et annulation des
  alternatives, actions métier et pipeline à quatre gardes,
  événements/kinds et armement after-commit, work-items de départ
  virtuels, passerelles, verrouillage coopératif, transitions runtime).
  Couverture : 9,2 % → 32,4 % (processinstance : 9/9 modules,
  60/63 classes, 175/321 fonctions). Résidu connu, laissé à la passe de
  relecture : les ~45 accesseurs quasi jumeaux d'`ExecutionContext`
  (documentés au niveau classe par leur grille de nommage) et quelques
  petits utilitaires. Suite : tranche 3 = `processdefinition/` +
  `descriptors/` + `relations/`.
