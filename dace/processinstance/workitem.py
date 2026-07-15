# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi

"""Work-items: the units of pending work.

``StartWorkItem`` is *virtual* — computed from startable paths before
any process instance exists; consuming it instantiates the process
(reusing the running one for ``isUnique`` definitions) and replays the
chosen path. ``WorkItem`` is the concrete unit attached to a node;
``DecisionWorkItem`` materialises one alternative of an exclusive
choice, and consuming it cancels its siblings.
"""
from pyramid.threadlocal import get_current_request
from pyramid.interfaces import ILocation
from zope.interface import implementer

from dace.util import find_service

from dace.interfaces import (
    IWorkItem, IStartWorkItem, IDecisionWorkItem)
from dace.objectofcollaboration.object import Object
from dace.descriptors import CompositeMultipleProperty
from .lock import LockableElement


class UserDecision(LockableElement):

    """A user-facing choice over a computed path.

    Holds the path and its initiating nodes; equal decisions (same path)
    are merged so one work-item can represent several initiators.
    """
    def __init__(self, decision_path, initiator):
        super(UserDecision, self).__init__()
        self.path = decision_path
        self.initiators = []
        self.initiators.append(initiator)

    @property
    def first_transitions(self):
        """The first transitions of the path, per initiator."""
        result = set()
        for initiator in self.initiators:
            result = result.union(self.path._get_transitions_source(initiator))

        return set(self.path.first).union(result)

    def merge(self, decision):
        """Absorb an equal decision (union of initiators, merged paths)."""
        self.initiators = set(self.initiators).union(decision.initiators)
        self.path = self.path.merge(decision.path)

    def concerned_nodes(self):
        """The nodes taking part in this decision (initiators + path sources)."""
        result = set(self.initiators).union(self.path.sources)
        return result

    def __eq__(self, other):
        return isinstance(other, UserDecision) and self.path.equal(other.path)

    def consume(self):# pragma: no cover
        """Consume hook (specialised by the concrete decisions)."""
        pass


@implementer(IStartWorkItem)
class StartWorkItem(UserDecision):

    """Virtual work-item offered before the process exists.

    Built from a startable path; instantiates the node's actions with
    ``dont_lock`` (nothing is in the ZODB yet — lock operations are
    deferred as callbacks, see ``LockableElement``).
    """
    def __init__(self, startable_path, initiator):
        super(StartWorkItem, self).__init__(startable_path, initiator)
        self.dont_lock = True
        self.node = self.path.targets[0]
        self.process = None
        self.actions = []
        actions = []
        for action_context in self.node.contexts:
            action = action_context(self)
            # The creation of the action can modify self.actions
            actions.append(action)

        self.actions.extend(actions)
        for action in self.actions:
            action.dont_lock = True

    @property
    def process_id(self):
        """The definition id this start belongs to."""
        return self.node.process.id

    @property
    def node_id(self):
        """The target node id of the startable path."""
        return self.node.id

    def consume(self):
        """Materialise the start: reuse the running instance for ``isUnique``
        definitions, otherwise create the process, register it in the runtime,
        build its graph, start it and replay the chosen path
        (``Start`` + ``Replay`` sub-transactions); return ``(workitem,
        process)`` with the actions transferred.
        """
        def_container = find_service('process_definition_container')
        pd = def_container.get_definition(self.process_id)
        started_processes = pd.started_processes
        if pd.isUnique and started_processes:
            proc = started_processes[0]
            self.process = proc
            wi = proc[self.node.__name__]._get_workitem()
            if wi is None:
                return

            wi.set_actions(self.actions)
            if self.dont_lock:
                self.call(wi)

            return wi, proc

        proc = pd()
        runtime = find_service('runtime')
        proc.__name__ = proc.id
        runtime.addtoproperty('processes', proc)
        proc.defineGraph(pd)
        proc.start()
        self.process = proc
        self.path.transitions = [proc[t.__name__] \
                                for t in self.path.transitions]
        self.path._dirty()
        start_transaction = proc.global_transaction.start_subtransaction(
                            'Start', (self.path.first[0]), initiator=self)
        proc[self.path.sources[0].__name__].start(start_transaction)
        replay_transaction = proc.global_transaction.start_subtransaction(
                                  'Replay', path=self.path, initiator=self)
        proc.replay_path(self, replay_transaction)
        proc.global_transaction.remove_subtransaction(replay_transaction)
        wi = proc[self.node.__name__]._get_workitem()
        #wi.start(*args)
        return wi, proc

    def add_action(self, action):
        """Attach an extra action (kept unlocked) to this virtual work-item."""
        action.dont_lock = True
        action.workitem = self
        self.actions.append(action)

    def validate(self):
        """If all transitions (including incoming TODO) are async, return True
        Else if a one transition in the chain is sync,
        verify all transitions condition.
        """
        transitions = self.path.transitions
        if not [t for t in transitions if t.sync]:
            return True
        else:
            for transition in transitions:
                if transition.sync and not transition.validate(self.process):
                    return False

        return True

    def __eq__(self, other):
        return UserDecision.__eq__(self, other) and self.node is other.node


@implementer(ILocation)
class BaseWorkItem(LockableElement, Object):

    """Concrete work-item base: owned ``actions`` (composite), a node
    back-reference, and the action-transfer machinery used when a decision
    or start is consumed (``set_actions`` re-parents and runs the deferred
    lock callbacks).
    """
    actions = CompositeMultipleProperty('actions')
    context = None

    def __init__(self, node):
        LockableElement.__init__(self)
        Object.__init__(self)
        self.node = node
        self.is_valide = True

    def _init_actions(self):
        """Instantiate the node definition's action contexts as owned actions."""
        for action_context in self.node.definition.contexts:
            action = action_context(self)
            action.__name__ = action.behavior_id
            self.addtoproperty('actions', action)

    @property
    def process_id(self):
        """The process id (via the node)."""
        return self.node.process.id

    @property
    def node_id(self):
        """The node id."""
        return self.node.id

    @property
    def process(self):
        """The process instance (via the node)."""
        return self.node.process

    def start(self):
        """Start hook (generated work-items override it)."""
        pass # pragma: no cover

    def add_action(self, action):
        """Adopt ``action`` (moving it from its previous holder if any)."""
        action.workitem = self
        if getattr(action, '__parent__', None):
            action.__parent__.move(
                action.__name__, (self, 'actions'),
                newname=action.behavior_id)
        else:
            action.__name__ = action.behavior_id
            self.addtoproperty('actions', action)

    def set_actions(self, actions):
        """Replace the actions, running the deferred lock callbacks."""
        self.setproperty('actions', [])
        for action in actions:
            self.add_action(action)
            if getattr(action, 'dont_lock', False):
                action.dont_lock = False
                action.call(action)

    def validate(self):
        """Is this work-item currently consumable? (specialised)."""
        raise NotImplementedError # pragma: no cover

    def concerned_nodes(self):
        """The nodes this work-item concerns (itself)."""
        return {self.node}


@implementer(IWorkItem)
class WorkItem(BaseWorkItem):
    """This is subclassed in generated code.
    """
    context = None

    def __init__(self, node):
        super(WorkItem, self).__init__(node)

    def start(self):
        raise NotImplementedError # pragma: no cover

    def validate(self):
        """If all transitions (including incoming TODO) are async, return True
        Else if a one transition in the chain is sync,
        verify all transitions condition.
        """
        global_request = get_current_request()
        return True and not self.is_locked(global_request)

    def start_test_activity(self): #for tests
        """Test helper: finish the behaviour immediately."""
        self.node.finish_behavior(self)

    def start_test_empty(self): #for tests
        """Test helper: no-op start."""
        pass

    def __eq__(self, other):
        return isinstance(other, WorkItem) and self.node is other.node


@implementer(IDecisionWorkItem)
class DecisionWorkItem(BaseWorkItem, UserDecision):

    """One alternative of an exclusive choice, as a persistent work-item.

    ``validations`` records the gateways that validated it; when every
    concerned node has, the decision ``is_finished``. ``consume`` replays
    the chosen path (handling the raced-away case where a sibling consumer
    already removed it).
    """
    def __init__(self, decision_path, node, initiator):
        BaseWorkItem.__init__(self, node)
        UserDecision.__init__(self, decision_path, initiator)
        self.validations = []
        self._init_actions()

    @property
    def is_finished(self):
        """True when no concerned node remains to validate."""
        return not self.concerned_nodes()

    def consume(self):
        """Replay the chosen path and return the real work-item of the target
        node; if a concurrent consumer already removed this decision, just
        transfer the actions to the existing work-item.
        """
        if self.__parent__ is None: # deleted by another consumer
            wi = self.process[self.node.__name__]._get_workitem()
            if wi is not None:
                wi.set_actions(self.actions)

            return wi

        replay_transaction = self.process.global_transaction.start_subtransaction(
                                    'Replay', path= self.path, initiator=self)
        self.process.replay_path(self, replay_transaction)
        self.process.global_transaction.remove_subtransaction(replay_transaction)
        wi = self.process[self.node.__name__]._get_workitem()
        return wi

    def validate(self):
        """If all transitions (including incoming TODO) are async, return True
        Else if a one transition in the chain is sync,
        verify all transitions condition.
        """
        global_request = get_current_request()
        transitions = self.path.transitions
        if not [t for t in transitions if t.sync]:
            return True and not self.is_locked(global_request)
        else:
            for transition in transitions:
                if transition.sync and not transition.validate(self.process):
                    return False

        return True and not self.is_locked(global_request)

    def concerned_nodes(self):
        """Concerned nodes not yet validated."""
        result = set(self.initiators).union(self.path.sources)
        return {n for n in result if not n in self.validations}

    def __eq__(self, other):
        return   UserDecision.__eq__(self, other) and self.node is other.node
