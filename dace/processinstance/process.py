from persistent import Persistent
from persistent.list import PersistentList
from pyramid.threadlocal import get_current_registry
from substanced.util import get_oid
from zope.interface import implements
import transaction

from .activity import SubProcess
from .event import Event
from .core import ProcessStarted
from dace.processdefinition.core import Transaction
from dace.processdefinition.eventdef import EventHandlerDefinition
from dace.objectofcollaboration.entity import Entity
from .gateway import ExclusiveGateway
from dace.interfaces import IProcess, IProcessDefinition, IWorkItem
from dace.relations import find_relations, connect
from .transition import Transition
from dace.util import find_catalog
from dace.objectofcollaboration.object import COMPOSITE_MULTIPLE, COMPOSITE_UNIQUE, SHARED_MULTIPLE, SHARED_UNIQUE, Object


class ExecutionContext(Object):

    properties_def = {'createds': (SHARED_MULTIPLE, 'creator', True),
                      'involveds': (SHARED_MULTIPLE, 'involvers', True),
                      'process': (SHARED_UNIQUE, 'execution_context', True),
                      }

    def __init__(self):
        super(ExecutionContext, self).__init__()
        self.parent = None
        self.sub_execution_contexts = PersistentList()

    @property
    def createds(self):
        return self.getproperty('createds')

    @property
    def involveds(self):
        return self.getproperty('involveds')

    @property
    def process(self):
        return self.getproperty('process')

    def add_sub_execution_context(self, ec):
        self.sub_execution_contexts.append(ec)
        ec.parent = self

    def remove_sub_execution_context(self, ec):
        self.sub_execution_contexts.remove(ec)
        ec.parent = None

#entity
    def add_involved_entity(self, name, value):
        self.addtoproperty('involveds', value)
        if name in self.dynamic_properties_def:
            self.addtoproperty(name, value)
        else:
            opposit_name = name+'_involver'
            self.dynamic_properties_def[name] = (SHARED_MULTIPLE, opposit_name, True)
            value.dynamic_properties_def[opposit_name] = (SHARED_UNIQUE, name, True)
            self._init__property(name, self.dynamic_properties_def[name])
            value._init__property(opposit_name, value.dynamic_properties_def[opposit_name])
            self.addtoproperty(name, value)

    def remove_involved_entity(self, name, value):
        self.delproperty('involveds', value)
        if name in self.dynamic_properties_def:
            self.delproperty(name, value)

    def get_involved_entity(self, name, index=-1):#TODO sub contexts and parent
        if name in self.dynamic_properties_def:
            result = self.getproperty(name)
            if result:
                return result[index]

        return None

    def get_involved_entities(self, name=None):#TODO sub contexts and parent
        if name is None:
            return self.involveds

        if name in self.dynamic_properties_def:
            result = self.getproperty(name)
            return result

        return []

    def add_created_entity(self, name, value):
        self.addtoproperty('createds', value)
        self.add_involved_entity(name, value)

    def remove_created_entity(self, name, value):
        self.delproperty('createds', value)
        self.remove_involved_entity(name, value)

    def get_created_entity(self, name, index=-1):#TODO sub contexts and parent
        if name in self.dynamic_properties_def:
            result = [e for e in self.getproperty(name) if e in self.createds]
            if result:
                return result[index]

        return None

    def get_created_entities(self, name=None):#TODO sub contexts and parent
        if name is None:
            return self.createds

        if name in self.dynamic_properties_def:
            result = [e for e in self.getproperty(name) if e in self.createds]
            return result

        return []

    def has_relation(self, value, name=None):#TODO sub contexts and parent
        if name is None:
            return value in self.involveds

        if name in self.dynamic_properties_def:
             return value in self.getproperty(name)
        else:
            return False
#collections

    def add_involved_collection(self, name, values):
        index_key = name+'_index'
        if not self.has_data(index_key):
            self.add_data(index_key, 0)
        
        index = self.get_data(index_key)+1
        self.add_data(index_key, index)
        name = name+'_'+str(index)
        for value in values:
            self.addtoproperty('involveds', value)
            if name in self.dynamic_properties_def:
                self.addtoproperty(name, value)
            else:
                opposit_name = name+'_involver'
                self.dynamic_properties_def[name] = (SHARED_MULTIPLE, opposit_name, True)
                value.dynamic_properties_def[opposit_name] = (SHARED_UNIQUE, name, True)
                self._init__property(name, self.dynamic_properties_def[name])
                value._init__property(opposit_name, value.dynamic_properties_def[opposit_name])
                self.addtoproperty(name, value)

    def remove_involved_collection(self, name, values):
        index_key = name+'_index'
        if not self.has_data(index_key):
            return
        
        index = self.get_data(index_key)
        name = name+'_'+str(index)
        for value in values:
            self.delproperty('involveds', value)
            if name in self.dynamic_properties_def:
                self.delproperty(name, value)

    def get_involved_collection(self, name, index=-1):#TODO sub contexts and parent
        index_key = name+'_index'
        if not self.has_data(index_key):
            return
        if index == -1:
            index = self.get_data(index_key)
        else:
            if index > self.get_data(index_key):
                return []

        name = name+'_'+str(index)
        if name in self.dynamic_properties_def:
            result = self.getproperty(name)
            return result

        return []

    def get_involved_collections(self, name=None):#TODO sub contexts and parent
        if name is None:
            return self.involveds

        index_key = name+'_index'
        result = []
        for index in range(self.get_data(index_key)) :
            result.append(self.get_involved_collection(name, (index+1)))
   
        return result

    def add_created_collection(self, name, values):
        for value in values:
            self.addtoproperty('createds', value)

        self.add_involved_collection(name, values)

    def remove_created_collection(self, name, values):
        for value in values:
            self.delproperty('createds', value)

        self.remove_involved_collection(name, values)

    def get_created_collection(self, name, index=-1):#TODO sub contexts and parent
        collections = self.get_involved_collection(name, index)
        if collections is None:
            return None

        result = [e for e in collections if e in self.createds]
        return result

    def get_created_collections(self, name=None):#TODO sub contexts and parent
        result = [[e for e in c if e in self.createds] for c in self.get_involved_collections(name)]
        return result
#Data
    def add_data(self, key, data):
        if not self.has_data(key):
            setattr(self, key, PersistentList())

        getattr(self, key).append(data)

    def get_data(self, key, index=-1):#TODO sub contexts and parent
        if self.has_data(key):
            datas = getattr(self, key)
            if index == -1 or index < len(datas): 
                return getattr(self, key)[index]

        return None

    def has_data(self, key):#TODO sub contexts and parent
        return hasattr(self, key)


class Process(Entity):
    implements(IProcess)

    properties_def = {'nodes': (COMPOSITE_MULTIPLE, 'process', True),
                      'transitions': (COMPOSITE_MULTIPLE, 'process', True),
                      'execution_context': (COMPOSITE_UNIQUE, 'process', True),
                      }

    _started = False
    _finished = False
    # l'instance d'activite (SubProcess) le manipulant
    attachedTo = None
    def __init__(self, definition, startTransition, **kwargs):
        super(Process, self).__init__(**kwargs)
        self.id = definition.id
        self.global_transaction = Transaction()
        self.startTransition = startTransition
        if not self.title:
            self.title = definition.id

        # do a commit so all events have a _p_oid
        # mail delivery doesn't support savepoint
        transaction.commit()

    def defineGraph(self, definition):
        for nodedef in definition.nodes:
            node = nodedef.create()
            node.id = nodedef.id
            node.__name__ = nodedef.__name__
            self.addtoproperty('nodes', node)
            if isinstance(nodedef, EventHandlerDefinition):
                node._init_boundaryEvents(nodedef)

        for transitiondef in definition.transitions:
            transition = transitiondef.create()
            transition.__name__ = transitiondef.__name__
            self.addtoproperty('transitions', transition)
            transition._init_ends(self, transitiondef)

    @property
    def nodes(self):
        return self.getproperty('nodes')

    @property
    def transitions(self):
        return self.getproperty('transitions')

    @property
    def execution_context(self):
        #if self.isSubProcess:
        #    return self.attachedTo.process.execution_context
        #else:
        #    return self.getproperty('execution_context')
        return self.getproperty('execution_context')


    def definition(self):
        registry = get_current_registry()
        return registry.getUtility(
            IProcessDefinition,
            self.id,
            )
    definition = property(definition)

    @property
    def isSubProcess(self):
        return self.definition.isSubProcess

    def replay_path(self, decision, transaction):
        path = decision.path
        first_transitions = decision.first_transitions
        self.replay_transitions(decision, first_transitions, transaction)
        executed_transitions = first_transitions
        next_transitions = set()
        for t in first_transitions:
            next_transitions = next_transitions.union(set(path.next(t)))

        for nt in next_transitions:
            if nt in executed_transitions:
                next_transitions.remove(nt)

        while next_transitions:
            self.replay_transitions(decision, next_transitions, transaction)
            executed_transitions.extend(next_transitions)
            next_ts = set()
            for t in next_transitions:
                next_ts = next_ts.union(set(path.next(t)))

            for nt in list(next_ts):
                if nt in executed_transitions:
                    next_ts.remove(nt)

            next_transitions = next_ts

    def replay_transitions(self,decision, transitions, transaction):
        executed_nodes = []
        for transition in transitions:
            node = transition.source
            if not (node in executed_nodes):
                executed_nodes.append(node)
                node.replay_path(decision, transaction)

    def getWorkItems(self):
        dace_catalog = find_catalog('dace')
        process_inst_uid_index = dace_catalog['process_inst_uid']
        object_provides_index = dace_catalog['object_provides']
        p_uid = get_oid(self, None)
        query = object_provides_index.any((IWorkItem.__identifier__,)) & \
                process_inst_uid_index.any((int(p_uid),))
        workitems = query.execute().all()
        result = {}
        self.result_multiple = {} # for tests
        for wi in workitems:
            if isinstance(wi.node, SubProcess) and wi.node.sub_processes:
                for sp in wi.node.sub_processes:
                    result.update(sp.getWorkItems())

            if wi.node.id in result:
                self.result_multiple[wi.node.id].append(wi)
            else:
                result[wi.node.id] = wi
                self.result_multiple[wi.node.id] = [wi]

        return result

    def getAllWorkItems(self, node_id=None):
        dace_catalog = find_catalog('dace')
        process_inst_uid_index = dace_catalog['process_inst_uid']
        object_provides_index = dace_catalog['object_provides']
        p_uid = get_oid(self, None)
        query = object_provides_index.any((IWorkItem.__identifier__,)) & \
                process_inst_uid_index.any((int(p_uid),))
        if node_id is not None:
            node_id_index = dace_catalog['node_id']
            query = query & node_id_index.eq(self.id+'.'+node_id)

        workitems = query.execute().all()
        result = []
        for wi in workitems:
            if isinstance(wi.node, SubProcess) and wi.node.sub_processes:
                for sp in wi.node.sub_processes:
                    result.extend(sp.getAllWorkItems())

            if not (wi in result):
                result.append(wi)

        return result


    def start(self):
        if self._started:
            raise TypeError("Already started")

        self.setproperty('execution_context', ExecutionContext())
        self._started = True
        registry = get_current_registry()
        registry.notify(ProcessStarted(self))

    def execute(self):
        start_events = [self[s.__name__] for s in self.definition._get_start_events()]
        for s in start_events:
            s.prepare()
            s.prepare_for_execution()
            if self._started:
                break

    def play_transitions(self, node, transitions):
        registry = get_current_registry()
        if transitions:
            for transition in transitions:
                next = transition.target
                registry.notify(transition)
                next.prepare()
                if isinstance(next, Event):
                    next.prepare_for_execution()

            for transition in transitions:
                next = transition.target
                starttransaction = self.global_transaction.start_subtransaction('Start', transitions=(transition,), initiator=transition.source)
                next(starttransaction)
                if self._finished:
                    break

    def __repr__(self):# pragma: no cover
        return "Process(%r)" % self.definition.id

