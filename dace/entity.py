from zope.component import getUtility, getUtilitiesFor
from zope.interface import implements
from zope.intid.interfaces import IIntIds
from persistent.list import PersistentList

from .interfaces import IEntity, IBusinessAction, IProcessDefinition
from .relations import ICatalog, any


class ActionCall(object):

    def __init__(self, action, obj):
        super(ActionCall, self).__init__()
        self.object = obj
        self.action = action
        self.title = self.action.title
        self.process = self.action.process
        #self.studyContent = self.action.studyContent(self.object)
        #self.reportContent = self.action.reportContent(self.object)
    @property
    def url(self):
        return self.action.url(self.object)

    @property
    def content(self):
        return self.action.content(self.object)


class Entity(object):
    implements(IEntity)

    def __init__(self, **kwargs):
        super(Entity, self).__init__(**kwargs)
        self.state = PersistentList()

    def setstate(self, state):
        if not isinstance(state, (list, tuple)):
            state = [state]
        self.state = PersistentList()
        for s in state:
            self.state.append(s)

    def getCreator(self):
        ids = getUtility(IIntIds)
        rcatalog = getUtility(ICatalog)
        relations = rcatalog.findRelations({
            u'target_id': ids.getId(self),
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
        ids = getUtility(IIntIds)
        rcatalog = getUtility(ICatalog)
        tags = [u"involved"]
        if tag is not None:
            tags = [t + tag for t in tags]
        opts = {u'target_id': ids.getId(self)}
        opts[u'tag'] = any(*tags)
        for relation in rcatalog.findRelations(opts):
            yield relation

    def getInvolvedProcessIds(self, tag=None):
        # amen debut
        intids = getUtility(IIntIds)

        for a in self.actions:
            if a.action.process is not None:
                yield intids.getId(a.action.process)
        # amen fin
        #for relation in self._getInvolvedProcessRelations(tag):
        #    yield relation.source_id

    def getInvolvedProcesses(self, tag=None):
        for relation in self._getInvolvedProcessRelations(tag):
            yield relation.source

    def getAllObject(self,):
        from zope.catalog.interfaces import ICatalog
        from zope.intid.interfaces import IIntIds
        from com.ecreall.omegsi.library import ResultSet
        catalog = getUtility(ICatalog)
        intids = getUtility(IIntIds)
        query = {'object_provides': {'any_of': (self.__dict__['dolmen.content.directives.schema'][0].__identifier__,)}}
        results = catalog.apply(query)
        return ResultSet(results, intids)

    @property
    def actions(self):
        from zope.catalog.interfaces import ICatalog
        from zope.intid.interfaces import IIntIds
        allactions = []
        catalog = getUtility(ICatalog)
        intids = getUtility(IIntIds)
        query = {'object_provides': {'any_of': (IBusinessAction.__identifier__,)}}
        results = list(catalog.apply(query))
        if len(results) > 0:
            for a in results:
                action = intids.getObject(a)
                if action.validate(self):
                    allactions.append(action)

        allprocess = getUtilitiesFor(IProcessDefinition)
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
