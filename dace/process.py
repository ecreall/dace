from persistent import Persistent
from persistent.list import PersistentList
from pyramid.threadlocal import get_current_registry
from substanced.util import get_oid
from zope.interface import implements
import transaction

from .activity import SubProcess
from .core import ProcessStarted
from .entity import Entity
from .gateway import ExclusiveGateway
from .interfaces import IProcess, IProcessDefinition, IWorkItem
from .relations import ICatalog, any, connect
from .transition import Transition
from .util import get_obj, find_catalog


class WorkflowData(Persistent):
    """Container for workflow-relevant and application-relevant data
    """


class Process(Entity, Persistent):
    implements(IProcess)
    _started = False
    _finished = False
    # l'instance d'activite (SubProcess) le manipulant
    attachedTo = None
    def __init__(self, definition, startTransition, **kwargs):
        super(Process, self).__init__(**kwargs)
        self.id = definition.id
        self.startTransition = startTransition
        self.nodes = {}
        for nodedef in definition.activities.values():
            node = nodedef.create(self)
            self.nodes[nodedef.id] = node
        self._p_changed = True

        self.workflowRelevantData = WorkflowData()
        self.workflowRelevantData.__parent__ = self
        if not self.title:
            self.title = definition.id

        # do a commit so all events have a _p_oid
        # mail delivery doesn't support savepoint
        transaction.commit()

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

    def getWorkItems(self):
        searchableworkitem_catalog = find_catalog('searchableworkitem')
        objectprovides_catalog = find_catalog('objectprovidesindexes')

        process_inst_uid_index = searchableworkitem_catalog['process_inst_uid']
        object_provides_index = objectprovides_catalog['object_provides']

        p_uid = get_oid(self, None)
        # TODO adapt query
        query = object_provides_index.any((IWorkItem.__identifier__,)) & 
                process_inst_uid_index.any((int(p_uid),))
        workitems = query.execute().all()

        d = {}
        for w in workitems:
            if isinstance(w.node, SubProcess):
                d.update(w.node.subProcess.getWorkItems())
            if w.node.id in d:
                raise Exception("We have several workitems for %s" % w.node.id)
            d[w.node.id] = w

        return d

#        return dict([(w.node.id, w) for w in workitems])

#    def start(self, *arguments):
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
        self.transition(None, (self.startTransition, ))

    def refreshXorGateways(self):
        for node in self.nodes:
            if isinstance(node, ExclusiveGateway):
                node._refreshWorkItems()

    def transition(self, node, transitions):
        registry = get_current_registry()
        if transitions:
            for transition in transitions:
                next = self.nodes[transition.to]
                registry.notify(Transition(node, next))
                next.prepare()

            for transition in transitions:
                next = self.nodes[transition.to]
                next(transition)
                if self._finished:
                    break

    def __repr__(self):
        return "Process(%r)" % self.id

    def getLastIndex(self, tag):
        if not hasattr(self.workflowRelevantData, tag + u"_index"):
            setattr(self.workflowRelevantData, tag + u"_index", 0)

        return self.getData(tag+u"_index")

    def nextIndex(self, tag):
        index = self.getLastIndex(tag)
        index = index + 1
        self.addData(tag + u"_index", index)
        return index

    def addData(self, key, data, loop=False):
        if self.isSubProcess:
            self.attachedTo.process.addData(key, data, loop)
        else:
            if not loop:
                setattr(self.workflowRelevantData, key, data)
            else:
                if not hasattr(self.workflowRelevantData, key):
                    setattr(self.workflowRelevantData, key, PersistentList())
                getattr(self.workflowRelevantData, key).append(data)

    def getData(self, key, loop=False, index=-1):
        if self.isSubProcess:
            return self.attachedTo.process.getData(key, loop, index)
        else:
            if not loop:
                return getattr(self.workflowRelevantData, key, None)
            else:
                return getattr(self.workflowRelevantData, key)[index]

    def _addRelation(self, entities, tags):
        if not isinstance(entities, (list, tuple)):
            entities = [entities]

        source = self
        for entity in entities:
            target = entity
            connect(source, target, tags=tags)

    def addCreatedEntities(self, entities, tag, index=-1):
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

    def addInvolvedEntities(self, entities, tag, index=-1):
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

    def _getEntityRelations(self, tags):
        registry = get_current_registry()
        if self.isSubProcess:
            yield self.attachedTo.process._getEntityRelations(tags)
        else:
            rcatalog = registry.getUtility(ICatalog)
            opts = {u'source_id': get_oid(self)}
            if tags is not None:
                opts[u'tag'] = any(*tags)
            for relation in rcatalog.findRelations(opts):
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

    def getInvolvedEntities(self, tag=None):
        if tag is not None:
            return self._getEntityRelations([u"involved" + tag])

        return self._getEntityRelations([u"involved"])

    def getInvolvedEntity(self, tag, index=-1):
        allTags = [u"involved" + tag]
        if index < 0:
            i = self.getLastIndex(tag)
            if i == 0:
                i = 1
            allTags = [t + unicode(i - 1) for t in allTags]
        else:
            allTags = [t + unicode(index) for t in allTags]

        return tuple(self._getEntityRelations(allTags))[0]

    def getAllCreatedEntities(self, tag=None):
        if tag is not None:
            return self._getEntityRelations([u"created"+tag])

        return self._getEntityRelations([u"created"])

    def hasRelationWith(self, entity, tag=None):
        tags = [u"involved"]
        if  tag is not None:
            tags = [t + tag for t in tags]
        for e in self._getEntityRelations(tags):
            if e == entity:
                return True
        return False

    def hasCreatedEntity(self, entity, tag=None):
        tags = [u"created"]
        if  tag is not None:
            tags = [t + tag for t in tags]
        for e in self._getEntityRelations(tags):
            if e == entity:
                return True
        return False
