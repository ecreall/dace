from zope.interface import implements
from persistent.list import PersistentList

from substanced.util import get_oid

from dace.interfaces import IEntity
from .object import Object
from dace.util import getAllBusinessAction
from dace.relations import find_relations


class ActionCall(object):
    # il faut faire ici un delegation des attribut de l'action en question
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

    #les relations avec le processus sont des relations d'agregation multiple bidirectionnelles
    # il faut donc les difinir comme des properties
    def getCreator(self):
        relations = find_relations({
            u'target_id': get_oid(self),
            u'tags': u"created"})
        return tuple(relations)[0].source

    def setCreator(self, creator, tag, index=-1):
        creator.addCreatedEntities(self, tag, index)

    def addInvolvedProcesses(self, processes, tag, index=-1):
        if not isinstance(processes, (list, tuple)):
            processes = [processes]

        for proc in processes:
            proc.addInvolvedEntities(self, tag, index)

    def _getInvolvedProcessRelations(self, tag=None, index=-1):
        tags = [u"involved"]
        if tag is not None:
            tags = [t + tag for t in tags]

        opts = {u'target_id': get_oid(self)}
        opts[u'tags'] = tags
        for relation in find_relations(opts):
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
        allactions = getAllBusinessAction(self)
        return [ActionCall(a, self) for a in allactions]
