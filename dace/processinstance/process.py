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
from dace.objectofcollaboration.object import COMPOSITE_MULTIPLE


class WorkflowData(Persistent):
    """Container for workflow-relevant and application-relevant data
    """


class Process(Entity):
    implements(IProcess)

    properties_def = {'nodes': (COMPOSITE_MULTIPLE, 'process', True),
                      'transitions': (COMPOSITE_MULTIPLE, 'process', True),
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
        self.workflowRelevantData = WorkflowData()
        self.workflowRelevantData.__parent__ = self
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
                self.result_multiple[wi.node.id].append(wi) #raise Exception("We have several workitems for %s" % wi.node.id)
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

#        return dict([(w.node.id, w) for w in workitems])

    def start(self):
        if self._started:
            raise TypeError("Already started")

        self._started = True
#        definition = self.definition
#        data = self.workflowRelevantData
#        args = arguments
#        for parameter in definition.parameters:
#            if parameter.input:
#                arg, args = args[0], args[1:]
#                setattr(data, parameter.__name__, arg)
#        if args:
#            raise TypeError("Too many arguments. Expected %s. got %s" %
#                            (len(definition.parameters), len(arguments)))

        registry = get_current_registry()
        registry.notify(ProcessStarted(self))
        #self.transition(None, (self.startTransition, ))

    def execute(self):
        start_events = [self[s.__name__] for s in self.definition._get_start_events()]
        for s in start_events:
            s.prepare()
            s.prepare_for_execution()
            if self._started:
                break

    def play_transitions(self, node, transitions):
        registry = get_current_registry()
        #transitions = [t.creat(self.process) for t in transitions]
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

    def __repr__(self):
        return "Process(%r)" % self.definition.id


############################################################################# gestion des relation
    def getLastIndex(self, tag):# pragma: no cover
        if not hasattr(self.workflowRelevantData, tag + u"_index"):
            setattr(self.workflowRelevantData, tag + u"_index", 0)

        return self.getData(tag+u"_index")

    def nextIndex(self, tag):# pragma: no cover
        index = self.getLastIndex(tag)
        index = index + 1
        self.addData(tag + u"_index", index)
        return index

    def addData(self, key, data, loop=False):# pragma: no cover
        if self.isSubProcess:
            self.attachedTo.process.addData(key, data, loop)
        else:
            if not loop:
                setattr(self.workflowRelevantData, key, data)
            else:
                if not hasattr(self.workflowRelevantData, key):
                    setattr(self.workflowRelevantData, key, PersistentList())
                getattr(self.workflowRelevantData, key).append(data)

    def getData(self, key, loop=False, index=-1):# pragma: no cover
        if self.isSubProcess:
            return self.attachedTo.process.getData(key, loop, index)
        else:
            if not loop:
                return getattr(self.workflowRelevantData, key, None)
            else:
                return getattr(self.workflowRelevantData, key)[index]

    def _addRelation(self, entities, tags):# pragma: no cover
        if not isinstance(entities, (list, tuple)):
            entities = [entities]

        source = self
        for entity in entities:
            target = entity
            connect(source, target, tags=tags)

    def addCreatedEntities(self, entities, tag, index=-1):# pragma: no cover
        if self.isSubProcess:
            self.attachedTo.process.addCreatedEntities(entities, tag, index)
        else:
            i = index
            if index < 0:
                i = self.getLastIndex(tag)
            allTags = [u"created", u"involved"]
            allTags.extend([t + tag for t in allTags])
            allTags.extend([t + unicode(i) for t in allTags])
            self._addRelation(entities, tags=allTags)

    def addInvolvedEntities(self, entities, tag, index=-1):# pragma: no cover
        if self.isSubProcess:
            self.attachedTo.process.addInvolvedEntities(entities, tag)
        else:
            i = index
            if index < 0:
                i = self.getLastIndex(tag)
            allTags = [u"involved"]
            allTags.extend([t + tag for t in allTags])
            allTags.extend([t + unicode(i) for t in allTags])
            self._addRelation(entities, tags=allTags)

    def _getEntityRelations(self, tags):# pragma: no cover
        if self.isSubProcess:
            yield self.attachedTo.process._getEntityRelations(tags)
        else:
            opts = {u'source_id': get_oid(self)}
            if tags is not None:
                opts[u'tag'] = tags
            for relation in find_relations(opts):
                yield relation.target

    def getCreatedEntity(self, tag, index=-1):
        allTags = [u"created" + tag]
        if index < 0:
            i = self.getLastIndex(tag)
            if i == 0:
                i = 1

            allTags = [t + unicode(i - 1) for t in allTags]
        else:
            allTags = [t + unicode(index) for t in allTags]

        return tuple(self._getEntityRelations(allTags))[0]

    def getInvolvedEntities(self, tag=None):# pragma: no cover
        if tag is not None:
            return self._getEntityRelations([u"involved" + tag])

        return self._getEntityRelations([u"involved"])

    def getInvolvedEntity(self, tag, index=-1):# pragma: no cover
        allTags = [u"involved" + tag]
        if index < 0:
            i = self.getLastIndex(tag)
            if i == 0:
                i = 1
            allTags = [t + unicode(i - 1) for t in allTags]
        else:
            allTags = [t + unicode(index) for t in allTags]

        return tuple(self._getEntityRelations(allTags))[0]

    def getAllCreatedEntities(self, tag=None):# pragma: no cover
        if tag is not None:
            return self._getEntityRelations([u"created"+tag])

        return self._getEntityRelations([u"created"])

    def hasRelationWith(self, entity, tag=None):# pragma: no cover
        tags = [u"involved"]
        if  tag is not None:
            tags = [t + tag for t in tags]
        for e in self._getEntityRelations(tags):
            if e == entity:
                return True
        return False

    def hasCreatedEntity(self, entity, tag=None):# pragma: no cover
        tags = [u"created"]
        if  tag is not None:
            tags = [t + tag for t in tags]
        for e in self._getEntityRelations(tags):
            if e == entity:
                return True
        return False
