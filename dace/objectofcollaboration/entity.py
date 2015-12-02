# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi

from BTrees.OOBTree import OOBTree
from zope.interface import implementer
from persistent.list import PersistentList

from dace.interfaces import IEntity
from dace.objectofcollaboration.object import Object
from dace.descriptors import SharedUniqueProperty, SharedMultipleProperty
from dace.util import getAllBusinessAction


class ActionCall(object):

    def __init__(self, action, context):
        super(ActionCall, self).__init__()
        self.context = context
        self.action = action
        self.title = self.action.title
        self.process = self.action.process

    @property
    def url(self):
        return self.action.url(self.context)


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

    def init_annotations(self):
        self.annotations = OOBTree()

    @property
    def state_or_none(self):
        return self.state if self.state else [None]

    @property
    def actions(self):
        allactions = getAllBusinessAction(self)
        return [ActionCall(a, self) for a in allactions]

    def setstate(self, state):
        if not isinstance(state, (list, tuple)):
            state = [state]

        self.state = PersistentList(state)
