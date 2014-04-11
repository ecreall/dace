from pyramid.threadlocal import get_current_registry, get_current_request
from pyramid.interfaces import ILocation
from zope.interface import implements, implementedBy
from zope.component.interfaces import IFactory

from dace.util import find_service

from dace.interfaces import (
    IWorkItem, IProcessDefinition, IStartWorkItem, IDecisionWorkItem)
from dace.objectofcollaboration.object import Object, COMPOSITE_MULTIPLE
from .lock import LockableElement



class WorkItemFactory(object):
    implements(IFactory)
    factory = NotImplemented
    title = u''
    description = u''

    def getInterfaces(self):
        return implementedBy(self.factory)

    def __call__(self, *args, **kw):
        return self.factory(*args, **kw)


class UserDecision(LockableElement):

    def __init__(self, decision_path):
        super(UserDecision, self).__init__()
        self.path = decision_path

    def merge(self, decision):
        self.path = self.path.merge(decision.path)

    def concerned_nodes(self):
        return self.path.sources

    def __eq__(self, other):
        return self.path.equal(other.path)


class StartWorkItem(UserDecision):
    implements(IStartWorkItem)


    def __init__(self, startable_path):
        super(StartWorkItem, self).__init__(startable_path)
        self.dtlock = True
        self.node = self.path.targets[0]
        self.process = None
        self.actions = []
        actions = []
        for a in self.node.contexts:
            action = a(self)
            # The creation of the action can modify self.actions
            actions.append(action)

        self.actions.extend(actions)
        for action in self.actions:
            action.dtlock = True

    @property
    def process_id(self):
        return self.node.process.id

    @property
    def node_id(self):
        return self.node.id

    def start(self, *args):
        registry = get_current_registry()
        pd = registry.getUtility(
                IProcessDefinition,
                self.process_id)
        proc = pd()
        runtime = find_service('runtime')
        runtime.addtoproperty('processes', proc)
        proc.defineGraph(pd)
        proc.start()
        self.process = proc
        self.path.transitions = [proc[t.__name__] for t in self.path.transitions]
        start_transaction = proc.global_transaction.start_subtransaction('Start', (self.path.first[0]), initiator=self)
        proc[self.path.sources[0].__name__].start(start_transaction)
        replay_transaction = proc.global_transaction.start_subtransaction('Replay', path=self.path, initiator=self)
        proc.replay_path(self, replay_transaction)
        proc.global_transaction.remove_subtransaction(replay_transaction)
        wi = proc[self.path.targets[0].__name__].workitems[0]
        #wi.start(*args)
        return wi, proc

    def add_action(self, action):
        action.dtlock = True
        action.workitem = self
        self.actions.append(action)

    def get_actions_validators(self):
        return [a.__class__.get_validator() for a in self.actions]

    def validate(self):
        # incoming transition is already checked
        return True

    def __eq__(self, other):
        return UserDecision.__eq__(self, other) and self.node is other.node


class BaseWorkItem(LockableElement, Object):
    implements(ILocation)

    properties_def = {'actions': (COMPOSITE_MULTIPLE, None, False)}
    context = None

    def __init__(self, node):
        LockableElement.__init__(self)
        Object.__init__(self)
        self.node = node

    def _init_actions(self):
        for a in self.node.definition.contexts:
            action = a(self)
            action.__name__ = action.behavior_id
            self.addtoproperty('actions', action)

    @property
    def actions(self):
        return self.getproperty('actions')

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
        action.__name__ = action.behavior_id
        action.workitem = self
        self.addtoproperty('actions', action)

    def set_actions(self, actions):
        self.setproperty('actions', [])
        for action in actions:
            self.add_action(action)
            if action.dtlock:
                action.dtlock = False
                action.call(action)

    def get_actions_validators(self):
        return [a.__class__.get_validator() for a in self.actions]

    def validate(self):
        raise NotImplementedError # pragma: no cover

    def concerned_nodes(self):
        return [self.node]


class WorkItem(BaseWorkItem):
    """This is subclassed in generated code.
    """
    implements(IWorkItem)
    context = None

    def __init__(self, node):
        super(WorkItem, self).__init__(node)

    def start(self, *args):
        raise NotImplementedError # pragma: no cover

    def validate(self):
        activity_id = self.node.definition.id
        node_def = self.node.definition
        if node_def.process.isControlled:
            return True

        # we don't have incoming transition it's a subprocess
        transition = [t for t in node_def.incoming
                if activity_id == t.target.id][0]
        proc = self.process
        global_request = get_current_request()
        return (not transition.sync or transition.condition(proc)) and not self.is_locked(global_request)


class DecisionWorkItem(BaseWorkItem, UserDecision):
    implements(IDecisionWorkItem)


    def __init__(self, decision_path, node):
        BaseWorkItem.__init__(self, node)
        UserDecision.__init__(self, decision_path)
        self.validations = []
        self._init_actions()

    @property
    def is_finished(self):
        return not self.concerned_nodes()

    def start(self, *args):
        replay_transaction = self.process.global_transaction.start_subtransaction('Replay', initiator=self)
        self.process.replay_path(self, replay_transaction)
        self.process.global_transaction.remove_subtransaction(replay_transaction)
        wi = self.process[self.path.targets[0].__name__].workitems[0]
        return wi

    def validate(self):
        """If all transitions (including incoming TODO) are async, return True
        Else if a one transition in the chain is sync,
        verify all transitions condition.
        """
        global_request = get_current_request() 
        transitions = self.path.transitions
        # TODO il faut verifier la condition
        if not [t for t in transitions if t.sync]:
            return True and not self.is_locked(global_request)
        else:
            for transition in transitions:
                if not transition.condition(self.process):
                    return False

        return True and not self.is_locked(global_request)
        
    def concerned_nodes(self):
        return [n for n in self.path.sources if not (n in self.validations)]

    def __eq__(self, other):
        return UserDecision.__eq__(self, other) and self.node is other.node
