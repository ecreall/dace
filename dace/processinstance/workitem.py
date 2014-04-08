from pyramid.threadlocal import get_current_registry
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


class StartWorkItem(LockableElement):
    implements(IStartWorkItem)


    def __init__(self, startable_path):
        super(StartWorkItem, self).__init__()
        self.path = startable_path
        self.node = self.path.targets[0]
        self.process = None
        self.actions = []
        self.dtlock = True
        actions = []
        for a in self.node.contexts:
            action = a(self)
            actions.append(action)

        self.actions.extend(actions)
        for action in self.actions:
            action.dtlock = True

    def add_action(self, action):
        action.dtlock = True
        self.actions.append(action)

    @property
    def process_id(self):
        return self.node.process.id

    @property
    def node_id(self):
        return self.node.id

    def merge(self, decision):
        self.path = self.path.merge(decision.path)

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
        start_transaction = proc.global_transaction.start_subtransaction('Start', (self.path.first[0]))
        proc[self.path.sources[0].__name__].start(start_transaction)
        replay_transaction = proc.global_transaction.start_subtransaction('Replay')
        proc.replay_path(self, replay_transaction)
        proc.global_transaction.remove_subtransaction(replay_transaction)
        wi = proc[self.path.targets[0].__name__].workitems[0]
        for action in self.actions:
            action.dtlock = False

        wi.setproperty('actions', self.actions)
        #wi.start(*args)
        return wi, proc

    def validate(self):
        # incoming transition is already checked
        return True

    def concerned_nodes(self):
        return self.path.sources

    def get_actions_validators(self):
        return [a.__class__.get_validator() for a in self.actions]


class BaseWorkItem(LockableElement, Object):
    implements(ILocation)

    properties_def = {'actions': (COMPOSITE_MULTIPLE, None, False)}
    context = None

    def __init__(self, node):
        LockableElement.__init__(self)
        Object.__init__(self)
        self.node = node

    def add_action(self, action):
        self.addtoproperty('actions', action)

    @property
    def actions(self):
        return self.getproperty('actions')

    def get_actions_validators(self):
        return [a.__class__.get_validator() for a in self.actions]

    @property
    def process_id(self):
        return self.node.process.id

    @property
    def node_id(self):
        return self.node.id

    @property
    def process(self):
        return self.node.process

    def validate(self):
        raise NotImplementedError

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
        raise NotImplementedError

    def validate(self):
        activity_id = self.node.definition.id
        node_def = self.node.definition
        if node_def.process.isControlled:
            return True

        # we don't have incoming transition it's a subprocess
        transition = [t for t in node_def.incoming
                if activity_id == t.target.id][0]
        proc = self.process
        return not transition.sync or transition.condition(proc)


class DecisionWorkItem(BaseWorkItem):
    implements(IDecisionWorkItem)


    def __init__(self, path, node):
        super(DecisionWorkItem, self).__init__(node)
        self.path = path
        self.validations = []
        actions = []
        for a in node.definition.contexts:
            action = a(self)
            actions.append(action)

        self.setproperty('actions', actions)
        
    def concerned_nodes(self):
        return [n for n in self.path.sources if not (n in self.validations)]

    @property
    def is_finished(self):
        return not self.concerned_nodes()

    def merge(self, decision):
        self.path = self.path.merge(decision.path)

    def start(self, *args):
        replay_transaction = self.process.global_transaction.start_subtransaction('Replay')
        self.process.replay_path(self, replay_transaction)
        self.process.global_transaction.remove_subtransaction(replay_transaction)
        wi = self.process[self.path.targets[0].__name__].workitems[0]
        wi.setproperty('actions', self.actions)
        return wi
        #results = args
        #self.path.source.workItemFinished(self, *results)

    def validate(self):
        """If all transitions (including incoming TODO) are async, return True
        Else if a one transition in the chain is sync,
        verify all transitions condition.
        """
        transitions = self.path.transitions
        # TODO il faut verifier la condition
        if not [t for t in transitions if t.sync]:
            return True
        else:
            for transition in transitions:
                if not transition.condition(self.process):
                    return False

        return True

    def __eq__(self, other):
        return self.path.equal(other.path) and self.node is other.node
