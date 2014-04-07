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
        self.path = startable_path
        self.process_id = self.path.sources[0].process.id
        self.node = self.path.targets[0]
        self.node_id = self.node.id
        self.node_name = self.node.__name__
        self.process = None
        registry = get_current_registry()
        pd = registry.getUtility(
                IProcessDefinition,
                self.process_id)
        self.actions = []
        for a in self.node.contexts:
            self.actions.append(a(self))

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
        proc.start()
        self.process = proc

        start_transaction = proc.global_transaction.start_subtransaction('Start', (self.path.first[0]))
        proc[self.path.sources[0].__name__].start(start_transaction)
        replay_transaction = proc.global_transaction.start_subtransaction('Replay')
        proc.replay_path(self, replay_transaction)
        proc.global_transaction.remove_subtransaction(replay_transaction)
        wi = proc[self.path.targets[0].__name__].workitems[0]
        #wi.start(*args)
        return wi, proc

    def lock(self, request):
        pass

    def unlock(self, request):
        pass

    def is_locked(self, request):
        return False

    def validate(self):
        # incoming transition is already checked
        return True

    def replay_path(self):
        pass

    def concerned_nodes(self):
        return self.path.sources


class BaseWorkItem(LockableElement, Object):
    implements(ILocation)

    properties_def = {'actions': (COMPOSITE_MULTIPLE, None, False)}
    context = None

    @property
    def actions(self):
        return self.getproperty('actions')

    def __init__(self, node):
        super(BaseWorkItem, self).__init__()
        self.node = node
        actions = []
        for a in node.definition.contexts:
            actions.append(a(self))
        self.setproperty('actions', actions)

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
        self.path = path
        self.validations = []
        super(DecisionWorkItem, self).__init__(node)

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

    def replay_path(self):
        pass
