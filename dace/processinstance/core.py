# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi

"""Runtime backbone of the engine.

Node lifecycle (``FlowNode`` and its refinements), user decisions
(``MakerFlowNode`` computing ``DecisionWorkItem``s over the definition
graph), behaviours (``Behavior``/``Wizard`` and their validation and
execution policy), and the engine's notification events
(``ProcessStarted``, ``ActivityExecuted``, ...) — including the
subscriber that appends each executed activity to the entity's
``process_history`` annotation (the data behind daceui's history view).
"""
import datetime
import pytz
import threading

from persistent import Persistent
from persistent.list import PersistentList
from pyramid.threadlocal import get_current_registry
from pyramid.interfaces import ILocation
from pyramid.events import subscriber
from zope.interface import implementer

from substanced.util import get_oid

from dace.interfaces import IProcessStarted, IProcessFinished
from dace import log
from dace.interfaces import IBehavior
from dace.descriptors import (
    CompositeMultipleProperty,
    SharedUniqueProperty, SharedMultipleProperty)
from dace.processdefinition.core import Path
from dace.objectofcollaboration.entity import Entity
from .workitem import DecisionWorkItem, StartWorkItem, WorkItem


PROCESS_HISTORY_KEY = 'process_history'


class BPMNElement(Entity):
    """Base of every runtime element: copies id/title/description from its definition."""
    def __init__(self, definition, **kwargs):
        super(BPMNElement,self).__init__(**kwargs)
        self.id = definition.id
        if not self.title:
            self.title = definition.title

        if not self.description:
            self.description = definition.description


@implementer(ILocation)
class FlowNode(BPMNElement):

    """A node of a running process.

    Relations: ``incoming``/``outgoing`` transitions, owned ``workitems``,
    back-reference ``process``. Subclasses implement ``start`` and the
    path-exploration hook ``find_executable_paths``. ``definition``
    resolves the matching node definition by name.
    """
    incoming = SharedMultipleProperty('incoming', 'target', False)
    outgoing = SharedMultipleProperty('outgoing', 'source', False)
    workitems = CompositeMultipleProperty('workitems', None, False)
    process = SharedUniqueProperty('process', 'nodes', False)

    def __init__(self, definition, **kwargs):
        super(FlowNode,self).__init__( definition, **kwargs)

    def prepare(self):
        """Notify ``ActivityPrepared`` (specialised by behavioural nodes)."""
        registry = get_current_registry()
        registry.notify(ActivityPrepared(self))

    def __call__(self, transaction):
        """Alias for ``start(transaction)`` — nodes are played by calling them."""
        self.start(transaction)

    def find_executable_paths(self, source_path, source):
        """Yield executable paths through this node (hook for path exploration)."""
        pass# pragma: no cover

    def start(self, transaction):
        """Run the node within the given (path) transaction. Abstract."""
        raise NotImplementedError# pragma: no cover

    def play(self, transitions):
        """Notify ``ActivityFinished`` and ask the process to play ``transitions``."""
        registry = get_current_registry()
        registry.notify(ActivityFinished(self))
        self.process.play_transitions(self, transitions)

    def replay_path(self, decision, transaction):
        """Hook used when re-playing a user-chosen path (see MakerFlowNode)."""
        pass# pragma: no cover

    def stop(self):
        """Stop hook (events, sub-processes); default: nothing to do."""
        pass# pragma: no cover

    @property
    def definition(self):
        """The node definition of the same name in the process definition."""
        return self.process.definition[self.__name__]

    def __repr__(self):# pragma: no cover
        return "%s(%r)" % (
            self.__class__.__name__,
            self.id
            )


class MakerFlowNode(FlowNode):

    """A node that produces user decisions.

    ``decide`` explores the outgoing graph (through ``Find``
    sub-transactions) and materialises each executable path as a
    ``DecisionWorkItem`` attached to this node; consuming one of them
    replays the chosen path and cancels the siblings
    (``finish_decisions``).
    """
    def __init__(self, definition, **kwargs):
        super(MakerFlowNode, self).__init__(definition, **kwargs)

    def decide(self, transaction):
        """Compute the decision work-items for the outgoing paths and attach them."""
        workitems = self._calculate_decisions(transaction)
        if not workitems:
            return

        for i, workitem in enumerate(workitems.values()):
            workitem.__name__ = i+1
            self.addtoproperty('workitems', workitem)

        for decision_workitem in workitems.values():
            node_to_execute = decision_workitem.node
            if hasattr(node_to_execute, 'prepare_for_execution'):
                node_to_execute.prepare_for_execution()

    def _calculate_decisions(self, transaction, transitions=None):
        """Explore ``transitions`` (default: all outgoing) and return a dict of
        ``DecisionWorkItem`` keyed by target-node name (merged when several
        paths reach the same node).
        """
        global_transaction = transaction.get_global_transaction()
        workitems = {}
        if transitions is None:
            transitions = self.outgoing

        for transition in transitions:
            if transition.sync or transition.validate(self.process):
                node = transition.target
                initial_path = Path([transition])
                global_transaction.start_subtransaction(type='Find', 
                                                    path=initial_path, 
                                                    initiator=self)
                executable_paths = node.find_executable_paths(
                                            initial_path, self)
                for executable_path in executable_paths:
                    dwi = DecisionWorkItem(executable_path, 
                           self.process[executable_path.targets[0].__name__],
                           self)
                    if dwi.node.__name__ in workitems:
                        workitems[dwi.node.__name__].merge(dwi)
                    else:
                        workitems[dwi.node.__name__] = dwi

        return workitems

    def refresh_decisions(self, transaction, transitions):
        """Recompute decisions for ``transitions`` and attach only the new ones."""
        workitems = self._calculate_decisions(transaction, transitions)
        new_workitems = [wi for wi in workitems.values() \
                         if not (wi in self.workitems)]
        if not  new_workitems:
            return

        for decision_workitem in new_workitems:
            node_to_execute = self.process[decision_workitem.node.__name__]
            if hasattr(node_to_execute, 'prepare_for_execution'):
                node_to_execute.prepare_for_execution()

        len_workitems = len(self.workitems)
        for i, workitem in enumerate(new_workitems):
            workitem.__name__ = i+1+len_workitems
            self.addtoproperty('workitems', workitem)

    def get_allconcernedworkitems(self):
        """All ``DecisionWorkItem`` of the process in which this node takes part."""
        allprocessworkitems = self.process.getAllWorkItems()
        result = [wi for wi in allprocessworkitems \
                 if isinstance(wi, DecisionWorkItem) and \
                    self in wi.concerned_nodes()]

        return result

    def replay_path(self, decision, transaction):
        """Find the concerned decision matching ``decision`` and finish it."""
        allconcernedkitems = self.get_allconcernedworkitems()
        for wi in allconcernedkitems:
            if decision.path.is_segment(wi.path):
                decision = wi
                break

        if decision in allconcernedkitems:
            self.finish_decisions(decision)
        else:
            self.finish_decisions(None)

    def finish_decisions(self, work_item):
        """Consume the chosen decision and cancel the alternatives (specialised)."""
        pass


class BehavioralFlowNode(MakerFlowNode):

    """A node carrying business behaviours (activities and events).

    ``prepare`` creates the real ``WorkItem`` (transferring the actions
    carried by a consumed ``StartWorkItem``/decision when re-playing);
    ``finish_behavior`` closes it, cleans the ``Start`` paths and triggers
    ``decide`` for what follows.
    """
    def __init__(self, definition, **kwargs):
        super(BehavioralFlowNode, self).__init__(definition, **kwargs)

    def find_executable_paths(self, source_path, source):
        """A behavioural node ends the exploration: yield the path as a decision."""
        decision_path = source_path.clone()
        source_transaction = source_path.transaction.__parent__
        source_transaction.remove_subtransaction(source_path.transaction)
        yield decision_path

    def _get_workitem(self):
        """Return a valid ``WorkItem`` for this node, consuming a valid
        ``DecisionWorkItem`` into a real one if needed; ``None`` otherwise.
        """
        workitems = [w for w in self.workitems if w.validate() and \
                     isinstance(w, WorkItem)]
        if workitems:
            return workitems[0]

        workitems = [w for w in self.process.getAllWorkItems(
                                              node_id=self.__name__) \
                     if w.validate()]
        if workitems:
            wi = workitems[0]
            if isinstance(wi, DecisionWorkItem):
                wi = wi.consume()
                if wi is not None:
                    self.addtoproperty('workitems', wi)

                return wi

        return None

    def prepare(self):
        """Create the node work-item, wiring actions from the initiating decision."""
        paths = self.process.global_transaction.find_allsubpaths_for(
                                                       self, 'Replay')
        user_decision = None
        if paths:
            user_decision = paths[0].transaction.initiator

        registry = get_current_registry()
        registry.notify(ActivityPrepared(self))
        workitem = WorkItem(self)
        workitem.id = 1
        workitem.__name__ = str(1)
        self.addtoproperty('workitems', workitem)
        if user_decision is not None:
            actions = user_decision.actions
            workitem.set_actions(actions)
            if getattr(user_decision, 'dont_lock', False):
                user_decision.call(workitem)
        else:
            workitem._init_actions()

    def start(self, transaction):
        registry = get_current_registry()
        registry.notify(ActivityStarted(self))

    def finish_behavior(self, work_item):
        """Close ``work_item``, notify, clean ``Start`` paths, then ``decide``."""
        if work_item  and not isinstance(work_item, StartWorkItem):
            self.delfromproperty('workitems', work_item)

        registry = get_current_registry()
        registry.notify(WorkItemFinished(work_item))
        paths = self.process.global_transaction.find_allsubpaths_for(
                                                        self, 'Start')
        if paths:
            for path in set(paths):
                source_transaction = path.transaction.__parent__
                source_transaction.remove_subtransaction(path.transaction)

        self.decide(self.process.global_transaction)

    def finish_decisions(self, work_item):
        """Validate the chosen decision, cancel the sibling decisions sharing its
        first transitions, play the chosen transition and clean ``Find`` paths.
        """
        if work_item is not None:
            # _get_transitions_source returns a set, convert it to list to
            # retrieve the first item in the code at the end
            first_transitions = list(work_item.path._get_transitions_source(self))
            work_item.validations.append(self)
            if work_item.is_finished:
                work_item.__parent__.delfromproperty('workitems', work_item)

            # clear common work items
            allconcernedworkitems = self.get_allconcernedworkitems()
            all_stoped_wis = []
            for cdecision in allconcernedworkitems:
                for f_t in first_transitions:
                    if cdecision.path.contains_transition(f_t):
                        if not (cdecision in all_stoped_wis) and \
                                cdecision is not work_item:
                            all_stoped_wis.append(cdecision)
                            cdecision.validations.append(self)
                            if cdecision.is_finished or \
                               not cdecision.path.is_segment(work_item.path):
                                # don't cdecision.node.stop()
                                cdecision.__parent__.delfromproperty(
                                           'workitems', cdecision)

                        break

            start_transition = first_transitions[0]
            self.process.play_transitions(self, [start_transition])
            paths = self.process.global_transaction.find_allsubpaths_by_source(
                                                                   self, 'Find')
            if paths:
                for path in paths:
                    if work_item.path.contains_transition(path.first[0]):
                        source_transaction = path.transaction.__parent__
                        source_transaction.remove_subtransaction(
                                                 path.transaction)


class Error(Exception):

    """Base error carrying a user-facing message, causes, solutions and a template."""
    principalmessage = NotImplemented
    causes = NotImplemented
    solutions = NotImplemented
    type = NotImplemented
    template = NotImplemented

    def __init__(self, **kwargs):
        super(Error, self).__init__()
        if 'msg' in kwargs:
            self.principalmessage = kwargs['msg']

        if 'causes' in kwargs:
            self.causes = kwargs['causes']

        if 'solutions' in kwargs:
            self.solutions = kwargs['solutions']

        if 'type' in kwargs:
            self.type = kwargs['type']

        if 'template' in kwargs:
            self.template = kwargs['template']


class ValidationError(Error):
    """Raised when an action refuses a context/user (see ``validate_action``)."""
    principalmessage = u""
    causes = []
    solutions = []
    type = 'danger'
    template = 'templates/message.pt'


class ExecutionError(Error):
    """Raised by a behaviour's ``start`` to abort its execution cleanly."""
    principalmessage = u""
    causes = []
    solutions = []
    type = 'danger'
    template = 'templates/message.pt'


class Validator(object):

    """Default action validator: always valid (see ``getBusinessActionValidator``)."""
    @classmethod
    def validate(cls, context, request, **kw):
        """Return True or raise ``ValidationError``."""
        return True


class Step(object):

    """A step of a ``Wizard`` behaviour, wired by micro-transitions."""
    def __init__(self, **kwargs):
        super(Step, self).__init__()
        self.wizard = None
        if 'wizard' in kwargs:
            self.wizard = kwargs['wizard']

        self.step_id = ''
        if 'step_id' in kwargs:
            self.step_id = kwargs['step_id']

        self._outgoing = PersistentList()
        self._incoming = PersistentList()

    def add_outgoing(self, transition):
        """Register an outgoing micro-transition."""
        self._outgoing.append(transition)

    def add_incoming(self, transition):
        """Register an incoming micro-transition."""
        self._incoming.append(transition)


@implementer(IBehavior)
class Behavior(Step):

    """Base class of every behaviour (business actions included).

    Class-level identity (``behavior_id``, ``title``); instance retrieval
    (``get_instance``); the execution policy ``execute`` = ``start`` +
    ``after_execution`` + ``redirect``, with ``ExecutionError`` handled.
    """
    title = NotImplemented
    description = NotImplemented
    behavior_id = NotImplemented

    def __init__(self, **kwargs):
        super(Behavior, self).__init__(**kwargs)
        if 'behavior_id' in kwargs:
            self.behavior_id = kwargs['behavior_id']

    @classmethod
    def get_instance(cls, context, request, **kw):
        """Return the behaviour instance (from the wizard steps if any)."""
        instance = None
        if 'wizard' in kw and kw['wizard'] is not None:
            wizard = kw['wizard']
            _stepinstances = dict([(s.behavior_id, s) for s in  \
                                   list(dict(wizard.stepinstances).values())])
            instance = _stepinstances[cls.behavior_id]
        else:
            instance = cls()

        return instance  # raise ValidationError if no action

    @classmethod
    def get_validator(cls, **kw):
        """Return the validator class used by views to pre-check the action."""
        return Validator  # defaultvalidator

    @property
    def _class_(self):
        """May be overrided later"""
        return self.__class__

    def validate(self, context, request, **kw):
        """Instance-level validation hook (default: valid)."""
        return True  # action instance validation

    def before_execution(self, context, request, **kw):
        pass  # pragma: no cover

    def start(self, context, request, appstruct, **kw):
        """Execution"""
        return {}

    def execute(self, context, request, appstruct, **kw):
        """Execution policy"""
        result_execution = {}
        try:
            result_execution = self.start(context, request, appstruct, **kw)
        except ExecutionError as error:
            self.after_execution(context, request, **kw)
            raise error

        kw.update(result_execution)
        self.after_execution(context, request, **kw)
        return self.redirect(context, request, **kw)

    def after_execution(self, context, request, **kw):
        pass  # pragma: no cover

    def cancel_execution(self, context, request, **kw):
        pass
        
    def redirect(self, context, request, **kw):
        pass  # pragma: no cover


def default_condition(context, request):
    """Default wizard-transition condition: always True."""
    return True


class Transition(Persistent):

    """Micro-transition between two wizard steps, guarded by ``condition``."""
    def __init__(self, 
                 source, 
                 target, 
                 id, 
                 condition=(lambda x, y:True), 
                 isdefault=False):
        self.wizard = source.wizard
        self.source = source
        self.target = target
        self.source.add_outgoing(self)
        self.target.add_incoming(self)
        self.condition = condition
        self.isdefault = isdefault
        self.id = id

    def validate(self, context, request, **args):
        """Evaluate the condition for (context, request)."""
        return self.condition(context, request, **args)


class Wizard(Behavior):
    """A behaviour made of ``steps`` linked by ``transitions``
    (tuples ``(source_id, target_id[, isdefault[, condition]])``),
    instantiated per action.
    """
    steps = {}
    transitions = ()

    def __init__(self, **kwargs):
        super(Wizard, self).__init__(**kwargs)
        self.transitionsinstances = PersistentList()
        self.stepinstances = PersistentList()
        for key, step in self.steps.items():
            stepinstance = step(step_id=key, wizard=self)
            self.stepinstances.append((stepinstance.step_id, stepinstance))

        _stepinstances = dict(self.stepinstances)
        for transition in self.transitions:
            sourceinstance = _stepinstances[transition[0]]
            targetinstance = _stepinstances[transition[1]]
            transitionid = transition[0]+'->'+transition[1]
            condition = None
            try:
                condition = transition[3]
            except Exception:
                condition = default_condition

            default = False
            try:
                default = transition[2]
            except Exception:
                pass

            transitioninstance = Transition(sourceinstance, targetinstance, 
                                            transitionid, condition, default)
            self.transitionsinstances.append((transitionid, transitioninstance))


class EventHandler(FlowNode):

    """A node that may carry boundary events (implementation unfinished — FIXME)."""
    def __init__(self, definition, **kwargs):
        super(EventHandler, self).__init__(definition, **kwargs)
        self.boundaryEvents = []  # PersistentList()

    def _init_boundaryEvents(self, definition):
        """Instantiate the boundary events of the definition (unfinished)."""
        self.boundaryEvents = [defi.create()
                for defi in definition.boundaryEvents]
        for bedef in definition.boundaryEvents:
            beinstance = bedef.create()
            beinstance.id = bedef.id
            beinstance.__name__ = bedef.__name__
            # FIXME: the implementation is unfinished
            self.process.addtoproperty('nodes', beinstance)

DEFAULTMAPPING_ACTIONS_VIEWS = {}

@implementer(IProcessStarted)
class ProcessStarted:

    """Engine event: a process instance started."""
    def __init__(self, process):
        self.process = process

    def __repr__(self):# pragma: no cover
        return "ProcessStarted(%r)" % self.process


@implementer(IProcessFinished)
class ProcessFinished:

    """Engine event: a process instance finished."""
    def __init__(self, process):
        self.process = process

    def __repr__(self):# pragma: no cover
        return "ProcessFinished(%r)" % self.process


class WorkItemFinished:

    """Engine event: a work-item was consumed/closed."""
    def __init__(self, workitem):
        self.workitem =  workitem

    def __repr__(self):# pragma: no cover
        return "WorkItemFinished(%r)" % self.node_id


class ActivityPrepared:

    """Engine event: a node prepared its work-item."""
    def __init__(self, activity):
        self.activity = activity

    def __repr__(self):# pragma: no cover
        return "ActivityPrepared(%r)" % self.activity


class ActivityFinished:

    """Engine event: a node finished."""
    def __init__(self, activity):
        self.activity = activity

    def __repr__(self):# pragma: no cover
        return "ActivityFinished(%r)" % self.activity


class ActivityStarted:

    """Engine event: a node started."""
    def __init__(self, activity):
        self.activity = activity

    def __repr__(self):# pragma: no cover
        return "ActivityStarted(%r)" % self.activity


class ActivityExecuted:

    """Engine event: a business action ran, with its contexts and user."""
    def __init__(self, activity, contexts, user):
        self.activity = activity
        self.contexts = contexts
        self.user = user

    def __repr__(self):# pragma: no cover
        return "ActivityExecuted(%r)" % self.activity


class ProcessError(Exception):
    """An error occurred in execution of a process.
    """


@subscriber(ActivityPrepared)
@subscriber(ActivityStarted)
@subscriber(ActivityFinished)
def activity_handler(event):# pragma: no cover
    """Log node lifecycle events (debug aid)."""
    log.info('%s %s', threading.current_thread().ident, event)


@subscriber(ActivityExecuted)
def activity_executed__handler(event):
    """Append the executed activity to each entity's ``process_history``
    annotation (date, state, user, activity ids/titles) — the source of
    daceui's process-history view.
    """
    now = datetime.datetime.now(tz=pytz.UTC)
    for context in event.contexts:
        if isinstance(context, Entity):
            process = event.activity.process
            node = event.activity.node
            node = {
                'date': now,
                'state': list(context.state),
                'user': get_oid(event.user, None),
                'activity_id': (event.activity.process_id,
                                event.activity.node_id),
                'activity_data': (getattr(process, 'title', None),
                                  getattr(node, 'title', None))
            }
            if not hasattr(context, 'annotations'):
                context.init_annotations()

            context.annotations.setdefault(
                PROCESS_HISTORY_KEY, PersistentList()).append(node)
