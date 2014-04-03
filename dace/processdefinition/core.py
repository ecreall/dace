from persistent import Persistent
from pyramid.threadlocal import get_current_registry
from pyramid.interfaces import ILocation
from pyramid.events import subscriber
from zope.interface import implements, Attribute
from zope.component import createObject
from substanced.event import ObjectAdded
import thread

from dace.interfaces import IRuntime, IProcessStarted, IProcessFinished
from dace.processinstance.workitem import DecisionWorkItem, StartWorkItem
from dace.processinstance.core import EventHandler
from dace import log
from dace.objectofcollaboration.object import Object, SHARED_MULTIPLE, SHARED_UNIQUE

class BPMNElementDefinition(Object):
    def __init__(self):
        super(BPMNElementDefinition, self).__init__()


class FlowNodeDefinition(BPMNElementDefinition):

    properties_def = {'incoming': (SHARED_MULTIPLE, 'target', False),
                      'outgoing': (SHARED_MULTIPLE, 'source', False),
                      'process': (SHARED_UNIQUE, 'nodes', False)
                      }
    #relation s_u opposite s_m avec les transitions 
    #relation s_u opposite c_m avec les Processdef 
    factory = Attribute("factory")
    incoming = ()
    outgoing = ()
    performer = ''

    def create(self, process):
        return self.factory(process, self)

    def __init__(self):
        super(FlowNodeDefinition, self).__init__()

    @property
    def incoming(self):
        return self.getproperty('incoming')

    @property
    def outgoing(self):
        return self.getproperty('outgoing')

    @property
    def process(self):
        return self.getproperty('process')

    def find_startable_paths(self, source_path, source):
        transition_path = [t for t in self.incoming if t.source is source][0]
        source_path.add_transition(transition_path)
        yield source_path

    def __repr__(self):
        return "<%s %r>" % (self.__class__.__name__, self.__name__)


class Transaction(Persistent):

    def __init__(self, type='Normal'):
        self.paths = []
        self.sub_transactions = []
        self.__parent__ = None
        self.type = type

    def add_paths(self, paths):
        if not isinstance(paths, (list, tuple)):
            paths = (paths, )

        self.paths.extend(paths)

    def add_subtransactions(self, subtransactions):
        if not isinstance(subtransactions, (list, tuple)):
            subtransactions = (subtransactions, )

        for sub_t in subtransactions:
            sub_t.__parent__ = self
    
        self.sub_transactions.extend(subtransactions)

    def remove_subtransaction(self, transaction):
        if self.sub_transactions and transaction in self.sub_transactions:
           self.sub_transactions.remove(transaction)

    def find_allsubpaths_for(self, node, type=None):
        result = self.find_subpaths_for(node, type)
        for subtransaction in self.sub_transactions:
            result.extend(subtransaction.find_allsubpaths_for(node, type))

        return result

    def find_subpaths_for(self, node, type=None):
        if type is None or type == self.type:
            return [p for p in self.paths if p.target is node]
        else:
            return []

    def find_allsubpaths(self, node, type=None):
        result = self.find_subpaths(node, type)
        for subtransaction in self.sub_transactions:
            result.extend(subtransaction.find_allsubpaths(node, type))

        return result

    def find_subpaths(self, node, type=None):
        if type is None or type == self.type:
            return [p for p in self.paths if p.contains(node)]
        else:
            return []

    def get_global_transaction(self):
        if self.__parent__ is None:
            return self

        return self.__parent__.get_global_transaction()

    def start_subtransaction(self, type='Normal', paths=None):
        path = None
        if paths is not None:
            if not isinstance(paths, (tuple, list)):
                paths = [paths]
            path = Path(self)
            path.add_transition(paths)

        transaction = Transaction(type)
        if path is not None:
            transaction.add_paths(path)

        self. add_subtransactions(transaction)
        return transaction
        

    def clean(self):
        self.path = []
        self.sub_transactions = []

class Path(object):

    def __init__(self, transaction):
        self.transaction = transaction
        transaction.add_paths(self)
        self.transitions = ()

    def add_transition(self, transition):
        if not isinstance(transition, (list, tuple)):
            transition = (transition, )

        self.transitions += transition

    @property
    def source(self):
        if self.transitions:
            return self.transitions[0].source
       
        return None

    @property
    def target(self):
        if self.transitions:
            return self.transitions[-1].target
       
        return None

    def clone(self):
        cloned = Path(self.transaction)
        cloned.add_transition(self.transitions)
        return cloned

    def is_segement(self, path):
        for transition in path.transitions:
            eqs = [t for t in self.transitions if t.equal(transition)]
            if not eqs:
                return False

        return True

    def contains(self, node):
        for t in self.transitions:
            if t.source is node or t.target is node:
                return True

        return False

    def _get_transitions_source(self, node):
        result = [t for t in self.transitions if t.source is node]
        result_set = []
        if result:
            result_set = [result.pop()]
            for t in result:
                eqs = [tt for tt in result_set if tt.equal(t)]
                if not eqs:
                    result_set.add(t)
                    result.remove(t)

        return result_set


    def _get_transitions_target(self, node):
        result = [t for t in self.transitions if t.target is node]
        result_set = []
        if result:
            result_set = [result.pop()]
            for t in result:
                eqs = [tt for tt in result_set if tt.equal(t)]
                if not eqs:
                    result_set.add(t)
                    result.remove(t)

        return result_set

    def get_multiple_target(self):
        results = set()
        for t in self.transitions:
            transitions = self._get_transitions(t.source)
            if len(transitions)>1:
                results.add(t.source)

        return results

class EventHandlerDefinition(FlowNodeDefinition):
    factory = EventHandler
    boundaryEvents = ()

    def __init__(self):
        super(FlowNodeDefinition, self).__init__()


class InvalidProcessDefinition(Exception):
    """A process definition isn't valid in some way.
    """
