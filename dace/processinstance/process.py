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

    properties_def = {'createds': (SHARED_MULTIPLE, 'creator', False),
                      'involveds': (SHARED_MULTIPLE, 'involvers', False),
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

    def root_execution_context(self):
        if self.parent is None:
            return self
        else:
            return self.parent.root_execution_context()

    def add_sub_execution_context(self, ec):
        if not(ec in self.sub_execution_contexts): 
            self.sub_execution_contexts.append(ec)
            ec.parent = self

    def remove_sub_execution_context(self, ec):
        if ec in self.sub_execution_contexts: 
            self.sub_execution_contexts.remove(ec)
            ec.parent = None

    def _sub_involveds(self):
        result = list(self.involveds)
        for sec in self.sub_execution_contexts:
            result.extend(sec._sub_involveds())

        return set(result)

    def all_involveds(self):
        root = self.root_execution_context()
        return root._sub_involveds()

    def _sub_createds(self):
        result = list(self.createds)
        for sec in self.sub_execution_contexts:
            result.extend(sec._sub_createds())

        return set(result)

    def all_createds(self):
        root = self.root_execution_context()
        return root._sub_createds()

#entity
    def add_involved_entity(self, name, value):
        self.addtoproperty('involveds', value)
        if name in self.dynamic_properties_def:
            self._init__property(name, self.dynamic_properties_def[name])
            self.addtoproperty(name, value)
        else:
            opposit_name = name+'_involver'
            self.dynamic_properties_def[name] = (SHARED_MULTIPLE, opposit_name, True)
            value.dynamic_properties_def[opposit_name] = (SHARED_UNIQUE, name, True)
            self._init__property(name, self.dynamic_properties_def[name])
            value._init__property(opposit_name, value.dynamic_properties_def[opposit_name])
            self.addtoproperty(name, value)

    def remove_entity(self, name, value):
        if value in self.involveds:
            self.delproperty('involveds', value)

        if value in self.createds:
            self.delproperty('createds', value)

        if name in self.dynamic_properties_def:
            self._init__property(name, self.dynamic_properties_def[name])
            self.delproperty(name, value)

    def add_created_entity(self, name, value):
        self.addtoproperty('createds', value)
        self.add_involved_entity(name, value)

    # involved_entity start
    def involved_entity(self, name, index=-1):
        result = self.get_involved_entity(name, index)
        if result is not None:
            return result
      
        result = self.find_involved_entity(name, index)
        if result:
            return result[0]

    def get_involved_entity(self, name, index=-1):
        if name in self.dynamic_properties_def:
            self._init__property(name, self.dynamic_properties_def[name])
            result = self.getproperty(name)
            if result and index < len(result):
                return result[index]

        collection = self.get_involved_collection(name, index)
        if collection:
            return collection[0]

        return None

    def find_subinvolved_entity(self, name, index=-1):
        result = self.get_involved_entity(name, index)
        if result is not None :
            return [result]
        else:
            result = []
            for sec in self.sub_execution_contexts:
                result.extend(sec.find_subinvolved_entity(name, index))

        return result

    def find_involved_entity(self, name, index=-1):
        root = self.root_execution_context()
        return root.find_subinvolved_entity(name, index)
    # involved_entity end

    # involved_entities start
    def involved_entities(self, name=None):
        result = self.get_involved_entities(name)
        if result :
            return result
      
        result = self.find_involved_entities(name)
        return result

    def get_involved_entities(self, name=None):
        if name is None:
            return list(self.involveds)

        if name in self.dynamic_properties_def:
            self._init__property(name, self.dynamic_properties_def[name])
            result = self.getproperty(name)
            return result

        result = []
        collections = self.get_involved_collections(name)
        for c in collections:
            result.extend(c)

        return result

    def find_subinvolved_entities(self, name=None):
        result = self.get_involved_entities(name)
        if result:
            return result
        else:
            for sec in self.sub_execution_contexts:
                result.extend(sec.find_subinvolved_entities(name))

        return result

    def find_involved_entities(self, name=None):
        root = self.root_execution_context()
        return root.find_subinvolved_entities(name)
    # involved_entities end

    # created_entity start
    def created_entity(self, name, index=-1):
        result = self.get_created_entity(name, index)
        if result is not None:
            return result
      
        result = self.find_created_entity(name, index)
        if result:
            return result[0]

        return None

    def get_created_entity(self, name, index=-1):
        if name in self.dynamic_properties_def:
            self._init__property(name, self.dynamic_properties_def[name])
            result = [e for e in self.getproperty(name) if e in self.createds]
            if result:
                return result[index]

        collection = self.get_created_collection(name, index)
        if collection:
            return collection[0]

        return None

    def find_subcreated_entity(self, name, index=-1):
        result = self.get_created_entity(name, index)
        if result is not None:
            return [result]
        else:
            result = []
            for sec in self.sub_execution_contexts:
                result.extend(sec.find_subcreated_entity(name, index))

        return result

    def find_created_entity(self, name, index=-1):
        root = self.root_execution_context()
        return  root.find_subcreated_entity(name, index)
    # created_entity end

    # created_entities start
    def created_entities(self, name=None):
        result = self.get_created_entities(name)
        if result :
            return result
      
        result = self.find_created_entities(name)
        return result

    def get_created_entities(self, name=None):
        if name is None:
            return list(self.createds)

        if name in self.dynamic_properties_def:
            self._init__property(name, self.dynamic_properties_def[name])
            result = [e for e in self.getproperty(name) if e in self.createds]
            return result

        return []

    def find_created_entities(self, name=None):
        root = self.root_execution_context()
        result_created = root.all_createds()
        result = [e for e in root.find_involved_entities(name) if e in result_created]
        return result
    # created_entities end

    # has relation_entity start
    def has_relation(self, value, name=None):
        if self.has_localrelation(value, name):
            return True

        return self.has_globalrelation(value, name)

    def has_subrelation(self, value, name=None):
        if self.has_localrelation(value, name):
            return True

        for sec in self.sub_execution_contexts:
            if sec.has_subrelation(value, name):
                return True

        return False

    def has_globalrelation(self, value, name=None):
        root = self.root_execution_context()
        return root.has_subrelation(value, name)

    def has_localrelation(self, value, name=None):
        if name is None:
            return value in self.involveds

        entities = self.get_involved_entities(name)
        if entities and value in entities:
            return True

        return False
    # has relation_entity end

#collections
    def add_involved_collection(self, name, values):
        index_key = name+'_index'
        if not hasattr(self, index_key):
            self.add_data(index_key, 0)
        
        index = self.get_localdata(index_key)+1
        self.add_data(index_key, index)
        name = name+'_'+str(index)
        for value in values:
            self.addtoproperty('involveds', value)
            if name in self.dynamic_properties_def:
                self._init__property(name, self.dynamic_properties_def[name])
                self.addtoproperty(name, value)
            else:
                opposit_name = name+'_involver'
                self.dynamic_properties_def[name] = (SHARED_MULTIPLE, opposit_name, True)
                value.dynamic_properties_def[opposit_name] = (SHARED_UNIQUE, name, True)
                self._init__property(name, self.dynamic_properties_def[name])
                value._init__property(opposit_name, value.dynamic_properties_def[opposit_name])
                self.addtoproperty(name, value)

    def remove_collection(self, name, values):
        index_key = name+'_index'
        if not hasattr(self, index_key):
            return
        
        index = self.get_localdata(index_key)
        name = name+'_'+str(index)
        for value in values:
            self.remove_entity(name, value)

    def add_created_collection(self, name, values):
        for value in values:
            self.addtoproperty('createds', value)

        self.add_involved_collection(name, values)

    # involved_collection start
    def involved_collection(self, name, index=-1):
        result = self.get_involved_collection(name, index)
        if result:
            return result
      
        result = self.find_involved_collection(name, index)
        if result:
            return result[0]

        return []

    def get_involved_collection(self, name, index=-1):
        index_key = name+'_index'
        if not hasattr(self, index_key):
            return []

        if index == -1:
            index = self.get_localdata(index_key)
        elif index > self.get_localdata(index_key):
            return []

        name = name+'_'+str(index)
        result = self.getproperty(name)
        return result

    def find_subinvolved_collection(self, name, index=-1):
        result = self.get_involved_collection(name, index)
        if result:
            return [result]
        else:
            for sec in self.sub_execution_contexts:
                result.extend(sec.find_subinvolved_collection(name, index))

        return result

    def find_involved_collection(self, name, index=-1):
        root = self.root_execution_context()
        return root.find_subinvolved_collection(name, index)
    # involved_collection end

    # involved_collections start
    def involved_collections(self, name=None):
        result = self.get_involved_collections(name)
        if result :
            return result
      
        result = self.find_involved_collections(name)
        return result

    def get_involved_collections(self, name=None):
        if name is None:
            return list(self.involveds)

        index_key = name+'_index'
        result = []
        if hasattr(self, index_key):
            for index in range(self.get_localdata(index_key)) :
                result.append(self.get_involved_collection(name, (index+1)))
   
        return result

    def find_subinvolved_collections(self, name=None):
        result = self.get_involved_collections(name)
        if result:
            return [result]
        else:
            result = []
            for sec in self.sub_execution_contexts:
                result.extend(sec.find_subinvolved_collections(name))

        return result

    def find_involved_collections(self, name=None):
        root = self.root_execution_context()
        return root.find_subinvolved_collections(name)
    # involved_collections end

    # created_collection start
    def created_collection(self, name, index=-1):
        result = self.get_created_collection(name, index)
        if result:
            return result
      
        result = self.find_created_collection(name, index)
        if result:
            return result[0]

        return []

    def get_created_collection(self, name, index=-1):
        collections = self.get_involved_collection(name, index)
        if not collections:
            return []

        result = [e for e in collections if e in self.createds]
        return result

    def find_subcreated_collection(self, name, index=-1):
        result = self.get_created_collection(name, index)
        if result:
            return [result]
        else:
            result = []
            for sec in self.sub_execution_contexts:
                result.extend(sec.find_subcreated_collection(name, index))

        return result

    def find_created_collection(self, name, index=-1):
        root = self.root_execution_context()
        return root.find_subcreated_collection(name, index)
    # created_collection end

    # created_collections start
    def created_collections(self, name=None):
        result = self.get_created_collections(name)
        if result :
            return result
       
        result = self.find_created_collections(name)
        return result

    def get_created_collections(self, name=None):
        if name is None:
            return list(self.createds)

        index_key = name+'_index'
        result = []
        if hasattr(self, index_key):
            for index in range(self.get_localdata(index_key)) :
                result.append(self.get_created_collection(name, (index+1)))
   
        return result

    def find_subcreated_collections(self, name):
        result = self.get_created_collections(name)
        if result:
            return [result]
        else:
            result = []
            for sec in self.sub_execution_contexts:
                result.extend(sec.find_subcreated_collections(name))

        return result

    def find_created_collections(self, name=None):
        root = self.root_execution_context()
        return root.find_subcreated_collections(name)
    # created_collections end


#Data
    def add_data(self, name, data):
        if not hasattr(self, name):
            setattr(self, name, PersistentList())

        getattr(self, name).append(data)

    def get_data(self, name, index=-1):
        data = self.get_localdata(name, index)
        if data is not None:
            return data 

        datas = self.find_data(name, index)
        return datas[0] 

    def get_localdata(self, name, index=-1):
        if hasattr(self, name):
            datas = getattr(self, name)
            if index == -1 or index < len(datas): 
                return getattr(self, name)[index]

        return None

    def find_subdata(self, name, index=-1):
        result = self.get_localdata(name, index)
        if result is not None :
            return [result]
        else:
            result = []
            for sec in self.sub_execution_contexts:
                result.extend(sec.find_subdata(name, index))

        return result

    def find_data(self, name, index=-1):
        root = self.root_execution_context()
        return root.find_subdata(name, index)


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

        execution_context = ExecutionContext()
        execution_context.__name__ = 'execution_context'
        self.setproperty('execution_context', execution_context)
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

