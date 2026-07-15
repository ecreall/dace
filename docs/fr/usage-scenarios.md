# DaCE — scénarios d'utilisation

*Compagnon de [`architecture.md`](architecture.md). Chaque extrait suit l'API réelle de la base legacy (ère Python 3.6) ; l'exemple de définition de processus reprend la suite de tests du moteur. English version: [`../en/usage-scenarios.md`](../en/usage-scenarios.md).*

## Scénario 1 — Câbler DaCE dans une application Pyramid

```ini
# production.ini / development.ini
pyramid.includes =
    substanced
    ...
    dace
```

`dace.includeme` fait alors : un scan du paquet (enregistrement des définitions de processus et des adaptateurs de catalogue), l'inclusion de `dace.system` (le réacteur démarre dès l'ouverture de la ZODB, via `IDatabaseOpenedWithRoot`), et l'enregistrement des étapes d'évolution. L'application hôte déclare ses propres définitions et behaviors dans des modules eux-mêmes scannés (nova-ideo le fait paquet de processus par paquet de processus, sous `novaideo/content/processes/`).

## Scénario 2 — Définir un processus

Les identifiants de nœuds sont les noms des arguments nommés de `defineNodes` ; les transitions référencent ces noms.

```python
from dace.processdefinition.processdef import ProcessDefinition
from dace.processdefinition.activitydef import ActivityDefinition
from dace.processdefinition.gatewaydef import (
    ExclusiveGatewayDefinition, ParallelGatewayDefinition)
from dace.processdefinition.eventdef import (
    StartEventDefinition, EndEventDefinition)
from dace.processdefinition.transitiondef import TransitionDefinition

pd = ProcessDefinition(**{'id': u'sample'})
pd.defineNodes(
    s  = StartEventDefinition(),
    a  = ActivityDefinition(),
    b  = ActivityDefinition(),
    g1 = ExclusiveGatewayDefinition(),
    g2 = ParallelGatewayDefinition(),
    e  = EndEventDefinition(),
)
pd.defineTransitions(
    TransitionDefinition('s', 'g1'),
    TransitionDefinition('g1', 'a'),
    TransitionDefinition('g1', 'g2'),
    TransitionDefinition('g2', 'b'),
    TransitionDefinition('a', 'e'),
    TransitionDefinition('b', 'e'),
)
```

Dans une application hôte, la définition est enregistrée via le décorateur venusian `process_definition` (voir n'importe quel `definition.py` des paquets de processus de nova-ideo) et atterrit dans `root['process_definition_container']` au démarrage ou par l'étape d'évolution. Les événements de début/fin manquants sont normalisés automatiquement ; les nœuds orphelins sont rejetés.

## Scénario 3 — Attacher une action métier à un contenu

Le motif nova-ideo, réduit à son squelette : un behavior applicable à une interface de contenu, gardé par jusqu'à quatre validateurs, lié à une activité de la définition de processus.

```python
from dace.processinstance.activity import InfiniteCardinality, ActionType

def submit_roles_validation(process, context):
    return has_role(role=('Owner', context))

def submit_processsecurity_validation(process, context):
    return global_user_processsecurity()

def submit_state_validation(process, context):
    return 'to work' in context.state

class SubmitIdea(InfiniteCardinality):
    context = Iidea                      # s'applique à tout objet fournissant Iidea
    roles_validation = submit_roles_validation
    processsecurity_validation = submit_processsecurity_validation
    state_validation = submit_state_validation

    def start(self, context, request, appstruct, **kw):
        context.state = PersistentList(['submitted'])
        context.reindex()                # garder le catalogue 'dace' synchronisé
        return {}
```

`InfiniteCardinality` signifie que l'action peut être exécutée un nombre illimité de fois tant que ses validateurs tiennent ; `ElementaryAction`/`LimitedCardinality` bornent le compte. Toute affectation de `context.state` **doit** être suivie de `context.reindex()` — l'état est un index, et tous les `state_validation` du site en dépendent.

## Scénario 4 — Demander « que puis-je faire ici ? » (la question de l'UI)

```python
from dace.util import getAllBusinessAction, getBusinessAction

actions = getAllBusinessAction(
    idea, request,
    process_id='ideamanagement',   # filtres optionnels
    node_id='submit')
for action in actions:
    action.execute(idea, request, {})   # ou rendre action.url / un formulaire
```

C'est le service cœur du moteur : requête de catalogue (`IBusinessAction` ∧ interfaces du contexte ∧ contextes potentiels) puis passage des validateurs. Pontus rend le résultat en formulaires/boutons ; daceui rend les panneaux de processus. `isautomatic=True` sélectionne les actions que le moteur exécute lui-même ; `action_type=ActionType.system` celles que le réacteur exécute.

## Scénario 5 — Événements temporels et conditionnels

Un événement intermédiaire **catching** suspend un chemin jusqu'à une échéance ou un prédicat :

```python
from dace.processdefinition.eventdef import (
    IntermediateCatchEventDefinition,
    TimerEventDefinition, ConditionalEventDefinition)

def deadline(process):
    return datetime.datetime.now() + datetime.timedelta(days=7)

pd.defineNodes(
    ...,
    reminder = IntermediateCatchEventDefinition(
        TimerEventDefinition(time_date=deadline)),
    quorum   = IntermediateCatchEventDefinition(
        ConditionalEventDefinition(condition=lambda process: ...)),
)
```

L'armement est transactionnel : le callback est enregistré via un **hook after-commit** (`push_event_callback_after_commit`), planifié sur l'IOLoop, exécuté par un `EventJob` sous l'identité système, avec rejeu en cas de conflit ZODB. Les événements en attente sont **réarmés au démarrage** (`start_intermediate_events`) : les échéances survivent aux redémarrages. Les itérations des groupes de travail de nova-ideo (« une semaine pour améliorer la proposition ») reposent exactement sur ce mécanisme.

## Scénario 6 — Processus système (façon crontab)

Une définition marquée `isUnique` et pilotée par des actions système se comporte comme un processus d'arrière-plan singleton : démarrée une fois, exécutée par le réacteur (index `issystem`, identité machine système ajoutée par `add_system_machine`). À utiliser pour la maintenance récurrente (digestion d'alertes, balayage des contenus expirés). L'étape `remove_unique_process_instances_evolve` existe précisément pour purger les instances singleton périmées lors des migrations.

## Scénario 7 — Rôles et visibilité

```python
from dace.objectofcollaboration.principal.util import (
    grant_roles, revoke_roles, has_role, get_users_with_role)

grant_roles(user, roles=('Moderator',))          # rôle global
grant_roles(user, roles=(('Owner', idea),))      # rôle local à un contexte
if has_role(role=('Owner', idea)):
    ...
```

Les rôles alimentent à la fois les validateurs (scénario 3) et les filtres de visibilité du catalogue : `get_access_keys(user)` précalcule les clés qu'une requête utilise, pour que les gros sites restent rapides. La hiérarchie est honorée (`has_role` accepte les supérieurs sauf `ignore_superiors=True`).

## Scénario 8 — Changer les définitions sur un site en production

1. Livrer le nouveau code (définitions modifiées).
2. Se connecter en super administrateur, ouvrir l'onglet *Database* de substanced et lancer **Evolve** (ou exécuter le script `sd_evolve`) : `process_definitions_evolve` resynchronise le conteneur de définitions, puis relance les mises à jour de catalogue.
3. **Redémarrer l'application** — le message de log de l'étape y insiste lui-même : les rétro-références `node_definition` portées par les classes de contenu ne sont reconstruites qu'au démarrage.

Sauter l'étape 3 est la façon classique d'obtenir un site qui ne « voit qu'à moitié » le nouveau processus.

## Scénario 9 — Harnais de test

`dace.testing` fournit le layer fonctionnel utilisé par la suite de dace elle-même (et par pontus/nova-ideo) : un `Configurator` Pyramid incluant substanced + dace sur une ZODB temporaire. Attention à un effet de bord de substanced documenté dans le fil de l'eau : son scan venusian importe les modules de test *de substanced*, qui importent `mock` — d'où `mock` dans l'extra `[test]`.
