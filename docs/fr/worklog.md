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


- Tranche 3 de la passe de docstrings : le métamodèle déclaratif
  (`dace/processdefinition/`), les descripteurs de relations
  (`dace/descriptors/`) et le catalogue de relations par oid
  (`dace/relations/`) — 177 docstrings après lecture intégrale des vingt
  modules. Points fixés par écrit : l'algèbre de chemins
  `Transaction`/`Path` (types, collecte récursive, topologie paresseuse
  et son invalidation `_dirty`), la normalisation du graphe et ses nœuds
  synthétiques (`startpg`, `endeg`, `mergepg`, `mergeeg` — les noms que
  daceui affiche), l'exploration des chemins démarrables côté définition
  derrière les work-items de départ virtuels, le re-parentage et la
  comptabilité `__property__` des quatre descripteurs, le `ResourceRef`
  défensif (fantômes de zeopack), et le rôle de `relations/` comme
  stockage des attributions de rôles (`reftype` toujours 'Role').
  Couverture : 32,4 % → 50,7 % (processdefinition 24/24 classes,
  descriptors 6/6, relations 17/17). Résidu : constructeurs, `__repr__`
  et quelques petits utilitaires. Suite : tranche 4 =
  `objectofcollaboration/` + `catalog/` + modules racine (`util.py` en
  tête).


- Tranche 4 — la dernière — de la passe de docstrings : la couche de
  collaboration (`dace/objectofcollaboration/`), le catalogue 'dace'
  (`dace/catalog/`) et les modules racine (`util.py` en tête, plus
  `wosystem.py`, `testing.py`, `interfaces.py`, `i18n/`) —
  164 docstrings après lecture intégrale. Fixé par écrit : le
  rétablissement de contexte des Job/EventJob et le passage d'arguments
  par oid, la socket de commande du réacteur (tcp://127.0.0.1:12345), le
  modèle d'attribution des rôles (relations 'Role' avec miroir racine,
  hiérarchie des supérieurs, clés d'accès `'<role>_<oid>'`), la
  synchronisation des définitions au démarrage et le recâblage
  `node_definition` qui rend le redémarrage obligatoire, la garde
  « nouvelles transactions » du crawler système, et les deux contrats
  d'adaptateurs derrière les 18 index du catalogue.
- **Passe de docstrings de la phase 2 close** : 7,8 % → 67,6 % au
  total — 60/60 modules, 163/180 classes, 432/727 fonctions. Le résidu
  non couvert relève d'une politique assumée : constructeurs,
  `__repr__`, souches de méthodes d'interface, et les grilles
  d'accesseurs quasi jumeaux (ExecutionContext, les cinq adaptateurs de
  recherche du catalogue) documentées au niveau classe. Prochains
  candidats de l'effort de documentation : la relecture humaine des
  quatre tranches, et l'extracteur BPMN→mermaid sur les 24 paquets de
  processus des applications hôtes.


## 16/07/2026 — Phase 3 / M1

- **dace est vert sur Python 3.12 : 88 tests, 0 échec, 0 erreur**, au
  premier run complet après le portage du réacteur. Pile moderne :
  substanced ressuscité depuis le git amont (s'installe en 1.0b1 sur
  3.12 — la surface de l'annexe A s'importe proprement, réduisant le
  fork à « lever le pin pyramid<2 plus tard ») ; pyramid tenu à 1.10.8
  par ce pin ; ZODB 6.3, BTrees 6.4, pyzmq 27, hypatia 0.5
  (`constraints-modern.txt`).
- Étape A du réacteur conforme au plan : fil de boucle asyncio, même
  transport de commandes zmq et même protocole picklé `(method, obj)` ;
  `DelayedCallback` sur `call_later` (`stop` thread-safe), le
  `Listener` des signaux est une tâche asyncio sur une socket SUB
  `zmq.asyncio`, `ConsumeTasks` possède une boucle privée par instance
  (isolation des tests plus propre que le singleton historique
  `IOLoop.instance()`). Le monkey-patch tornado du poll-timeout est
  supprimé ; les deux patches substanced sont vérifiés présents sur
  1.0b1.
- Suppressions/corrections : `rwproperty` → setters de propriété ;
  repli `pyramid.compat` ; l'import `pyramid.tests` du harnais remplacé
  par une politique d'authentification locale (les wheels modernes ne
  livrent plus les tests).
- Stratégie bi-pile : master est désormais 3.12 ; la preuve 3.6 vit sur
  le tag `legacy-golden-master` (job CI legacy épinglé dessus ; le
  buildout de KuneAgi épingle les trois checkouts de bibliothèques par
  révision). tox `py312` et job CI `py312-tests` requis ajoutés. Le
  test dédié de cadence crawler/repoll est différé : les tests
  existants de timers, conditionnels et signaux exercent de bout en
  bout l'ordonnancement porté.

- **Rafraîchissement documentaire.** Le README énonce la réalité
  bi-pile (88/88 sur les deux piles) ; l'architecture gagne la section
  pile moderne (réacteur asyncio étape A, shims, substanced depuis le
  git amont).
