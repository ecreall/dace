# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi

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

    def __init__(self, decision_path, initiator):
        super(UserDecision, self).__init__()
        self.path = decision_path
        self.initiators = []
        self.initiators.append(initiator)

    @property
    def first_transitions(self):
        result = set()
        for initiator in self.initiators:
            result = result.union(self.path._get_transitions_source(initiator))

        return list(set(self.path.first).union(result))

    def merge(self, decision):
        self.initiators = list(set(self.initiators).union(decision.initiators))
        self.path = self.path.merge(decision.path)

    def concerned_nodes(self):
        result = list(set(self.initiators).union(self.path.sources))
        return result

    def __eq__(self, other):
        return isinstance(other, UserDecision) and self.path.equal(other.path)

    def consume(self):# pragma: no cover
        pass


@implementer(IStartWorkItem)
class StartWorkItem(UserDecision):

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
        return self.node.process.id

    @property
    def node_id(self):
        return self.node.id

    def consume(self):
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

    actions = CompositeMultipleProperty('actions')
    context = None

    def __init__(self, node):
        LockableElement.__init__(self)
        Object.__init__(self)
        self.node = node
        self.is_valide = True

    def _init_actions(self):
        for action_context in self.node.definition.contexts:
            action = action_context(self)
            action.__name__ = action.behavior_id
            self.addtoproperty('actions', action)

    @property
    def process_id(self):
        return self.node.process.id

    @property
    def node_id(self):
        return self.node.id

    @property
    def process(self):
        return self.node.process

    def start(self):
        pass # pragma: no cover

    def add_action(self, action):
        action.workitem = self
        if getattr(action, '__parent__', None):
            action.__parent__.move(
                action.__name__, (self, 'actions'),
                newname=action.behavior_id)
        else:
            action.__name__ = action.behavior_id
            self.addtoproperty('actions', action)

    def set_actions(self, actions):
        self.setproperty('actions', [])
        for action in actions:
            self.add_action(action)
            if getattr(action, 'dont_lock', False):
                action.dont_lock = False
                action.call(action)

    def validate(self):
        raise NotImplementedError # pragma: no cover

    def concerned_nodes(self):
        return [self.node]


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
        self.node.finish_behavior(self)

    def start_test_empty(self): #for tests
        pass

    def __eq__(self, other):
        return isinstance(other, WorkItem) and self.node is other.node


@implementer(IDecisionWorkItem)
class DecisionWorkItem(BaseWorkItem, UserDecision):

    def __init__(self, decision_path, node, initiator):
        BaseWorkItem.__init__(self, node)
        UserDecision.__init__(self, decision_path, initiator)
        self.validations = []
        self._init_actions()

    @property
    def is_finished(self):
        return not self.concerned_nodes()

    def consume(self):
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
        result = set(self.initiators).union(self.path.sources)
        return [n for n in result if not (n in self.validations)]

    def __eq__(self, other):
        return   UserDecision.__eq__(self, other) and self.node is other.node
