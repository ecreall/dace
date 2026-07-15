# DaCE — usage scenarios

*Companion to [`architecture.md`](architecture.md). Every snippet follows the real API of the legacy code base (Python 3.6 era); the process-definition example mirrors the engine's own test suite. French version: [`../fr/usage-scenarios.md`](../fr/usage-scenarios.md).*

## Scenario 1 — Wire DaCE into a Pyramid application

```ini
# production.ini / development.ini
pyramid.includes =
    substanced
    ...
    dace
```

`dace.includeme` then: scans the package (registering process definitions and catalog adapters), includes `dace.system` (the reactor starts as soon as the ZODB is opened, via `IDatabaseOpenedWithRoot`), and registers the evolve steps. The host application declares its own definitions/behaviors in modules that are themselves scanned (nova-ideo does it per process package under `novaideo/content/processes/`).

## Scenario 2 — Define a process

Node ids are the keyword names given to `defineNodes`; transitions reference those names.

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

In a host application the definition is registered through the `process_definition` venusian decorator (see any `definition.py` under nova-ideo's process packages) and lands in `root['process_definition_container']` at startup or through the evolve step. Missing start/end events are normalised automatically; orphan nodes are rejected.

## Scenario 3 — Attach a business action to content

The nova-ideo pattern, reduced to its skeleton: a behavior applicable to a content interface, guarded by up to four validators, bound to an activity of the process definition.

```python
from dace.processinstance.activity import InfiniteCardinality, ActionType

def submit_roles_validation(process, context):
    return has_role(role=('Owner', context))

def submit_processsecurity_validation(process, context):
    return global_user_processsecurity()

def submit_state_validation(process, context):
    return 'to work' in context.state

class SubmitIdea(InfiniteCardinality):
    context = Iidea                      # applies to any object providing Iidea
    roles_validation = submit_roles_validation
    processsecurity_validation = submit_processsecurity_validation
    state_validation = submit_state_validation

    def start(self, context, request, appstruct, **kw):
        context.state = PersistentList(['submitted'])
        context.reindex()                # keep the 'dace' catalog in sync
        return {}
```

`InfiniteCardinality` means the action can be executed any number of times while its validators hold; `ElementaryAction`/`LimitedCardinality` bound the count. Setting `context.state` **must** be followed by `context.reindex()` — state is an index, and every `state_validation` in the site depends on it.

## Scenario 4 — Ask "what can I do here?" (the UI question)

```python
from dace.util import getAllBusinessAction, getBusinessAction

actions = getAllBusinessAction(
    idea, request,
    process_id='ideamanagement',   # optional filters
    node_id='submit')
for action in actions:
    action.execute(idea, request, {})   # or render action.url / a form
```

This is the engine's core service: catalog query (`IBusinessAction` ∧ context interfaces ∧ potential contexts) then validator run. Pontus renders the result as forms/buttons; daceui renders the process panels. `isautomatic=True` selects the actions the engine runs by itself; `action_type=ActionType.system` those the reactor runs.

## Scenario 5 — Timer and conditional events

An intermediate **catching** event suspends a path until a deadline or a predicate:

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

Arming is transactional: the callback is registered through an **after-commit hook** (`push_event_callback_after_commit`), scheduled on the IOLoop, executed by an `EventJob` under the system identity, with retry on ZODB conflict. Pending events are **re-armed at startup** (`start_intermediate_events`), so deadlines survive restarts. Nova-ideo's working-group iterations ("one week to improve the proposal") are exactly this mechanism.

## Scenario 6 — System (crontab-like) processes

A definition flagged `isUnique` and driven by system actions behaves as a singleton background process: started once, executed by the reactor (`issystem` index, system machine identity added by `add_system_machine`). Use it for recurring maintenance (alerts digestion, expired-content sweeps). The `remove_unique_process_instances_evolve` step exists precisely to purge stale singleton instances during migrations.

## Scenario 7 — Roles and visibility

```python
from dace.objectofcollaboration.principal.util import (
    grant_roles, revoke_roles, has_role, get_users_with_role)

grant_roles(user, roles=('Moderator',))          # global role
grant_roles(user, roles=(('Owner', idea),))      # context-local role
if has_role(role=('Owner', idea)):
    ...
```

Roles feed both the validators (Scenario 3) and the catalog visibility filters: `get_access_keys(user)` pre-computes the keys a query uses so that large sites stay fast. The hierarchy is honoured (`has_role` accepts superiors unless `ignore_superiors=True`).

## Scenario 8 — Changing definitions on a live site

1. Ship the new code (definitions changed).
2. Connect as super administrator, open substanced's *Database* tab and run **Evolve** (or run the `sd_evolve` script): `process_definitions_evolve` re-synchronises the definition container, then re-runs catalog updates.
3. **Restart the application** — the step's own log message insists on it: the `node_definition` back-references held by content classes are only rebuilt at startup.

Skipping step 3 is the classic way to get a site that "half sees" the new process.

## Scenario 9 — Test harness

`dace.testing` provides the functional layer used by dace's own suite (and by pontus/nova-ideo): a Pyramid `Configurator` including substanced + dace on a temporary ZODB. Beware of one substanced side effect documented in the worklog: its venusian scan imports substanced's *own* test modules, which import `mock` — hence `mock` in the `[test]` extra.
