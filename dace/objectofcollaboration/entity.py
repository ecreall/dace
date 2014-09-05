from zope.interface import implementer
from persistent.list import PersistentList
from pyramid.threadlocal import get_current_registry

from substanced.event import ObjectModified

from dace.interfaces import IEntity
from .object import Object
from dace.descriptors import SharedUniqueProperty, SharedMultipleProperty
from dace.util import getAllBusinessAction


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


class ProcessSharedUniqueProperty(SharedUniqueProperty):
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        res = super(ProcessSharedUniqueProperty, self).__get__(obj, objtype)
        if res is not None:
            return res.process

        return None


class ProcessSharedMultipleProperty(SharedMultipleProperty):
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        res = super(ProcessSharedMultipleProperty, self).__get__(obj, objtype)
        return [e.process for e in res]


@implementer(IEntity)
class Entity(Object):

    creator = ProcessSharedUniqueProperty('creator', 'createds', True)
    involvers = ProcessSharedMultipleProperty('involvers', 'involveds', True)

    def __init__(self, **kwargs):
        super(Entity, self).__init__(**kwargs)
        self.state = PersistentList()
        self.__property__ = None

    def setstate(self, state):
        if not isinstance(state, (list, tuple)):
            state = [state]

        self.state = PersistentList()
        for s in state:
            self.state.append(s)

    def reindex(self):
        event = ObjectModified(self)
        registry = get_current_registry()
        registry.subscribers((event, self), None)

    @property
    def actions(self):
        allactions = getAllBusinessAction(self)
        return [ActionCall(a, self) for a in allactions]

    #les relations avec le processus sont des relations d'agregation multiple bidirectionnelles
    # il faut donc les difinir comme des properties

