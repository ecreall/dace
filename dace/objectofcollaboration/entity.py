from zope.interface import implements
from persistent.list import PersistentList
from pyramid.threadlocal import get_current_registry

from substanced.util import get_oid

from dace.interfaces import IEntity, IBusinessAction, IProcessDefinition
from dace.relations import ICatalog, any
from .object import Object
from dace.util import find_catalog


class ActionCall(object):

    def __init__(self, action, obj):
        super(ActionCall, self).__init__()
        self.object = obj
        self.action = action
        self.title = self.action.title
        self.process = self.action.process

    @property
    def url(self):
        return self.action.url(self.object)

    @property
    def content(self):
        return self.action.content(self.object)


class Entity(Object):
    implements(IEntity)

    def __init__(self, **kwargs):
        Object.__init__(self)
        self.state = PersistentList()
        self.__property__ = None

    def setstate(self, state):
        if not isinstance(state, (list, tuple)):
            state = [state]

        self.state = PersistentList()
        for s in state:
            self.state.append(s)

    def getCreator(self):
        registry = get_current_registry()
        rcatalog = registry.getUtility(ICatalog)
        relations = rcatalog.findRelations({
            u'target_id': get_oid(self),
            u'tag': any(u"created")})
        return tuple(relations)[0].source

    def setCreator(self, creator, tag, index=-1):
        creator.addCreatedEntities(self, tag, index)

    def addInvolvedProcesses(self, processes, tag, index=-1):
        if not isinstance(processes, (list, tuple)):
            processes = [processes]

        for proc in processes:
            proc.addInvolvedEntities(self, tag, index)

    def _getInvolvedProcessRelations(self, tag=None, index=-1):
        registry = get_current_registry()
        rcatalog = registry.getUtility(ICatalog)
        tags = [u"involved"]
        if tag is not None:
            tags = [t + tag for t in tags]

        opts = {u'target_id': get_oid(self)}
        opts[u'tag'] = any(*tags)
        for relation in rcatalog.findRelations(opts):
            yield relation

    def getInvolvedProcessIds(self, tag=None):
        for a in self.actions:
            if a.action.process is not None:
                yield get_oid(a.action.process)

    def getInvolvedProcesses(self, tag=None):
        for relation in self._getInvolvedProcessRelations(tag):
            yield relation.source

    @property
    def actions(self):
        allactions = []
        dace_catalog = find_catalog('dace')
        context_id_index = dace_catalog['context_id']
        object_provides_index = dace_catalog['object_provides']
        query = object_provides_index.any((IBusinessAction.__identifier__,)) & \
                context_id_index.any(self.__provides__.declared)
        results = query.execute().all()
        if len(results) > 0:
            for action in results:
                if action.validate(self):
                    allactions.append(action)

        registry = get_current_registry()
        allprocess = registry.getUtilitiesFor(IProcessDefinition)
        # Add start workitem
        for name, pd in allprocess:
            if not pd.isControlled and (not pd.isUnique or (pd.isUnique and not pd.isInstantiated)):
                wis = pd.createStartWorkItem(None)
                for key in wis.keys():
                    swisactions = wis[key].actions
                    for action in swisactions:
                        if action.validate(self) :
                            allactions.append(action)

        return [ActionCall(a, self) for a in allactions]
