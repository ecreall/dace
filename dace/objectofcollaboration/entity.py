# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi

"""Entities: stateful collaboration objects.

``Entity`` adds the multi-valued ``state`` (a ``PersistentList``), the
dynamic ``actions`` (catalog-computed ``ActionCall``s), annotations
(the ``process_history`` store) and the ``creator``/``involvers``
properties, resolved through the execution contexts to the processes
that created/involved the entity.
"""
from BTrees.OOBTree import OOBTree
from zope.interface import implementer
from persistent.list import PersistentList

from dace.interfaces import IEntity
from dace.objectofcollaboration.object import Object
from dace.descriptors import SharedUniqueProperty, SharedMultipleProperty
from dace.util import getAllBusinessAction


class ActionCall(object):

    """A (business action, context) pair ready for the UI."""
    def __init__(self, action, context):
        super(ActionCall, self).__init__()
        self.context = context
        self.action = action
        self.title = self.action.title
        self.process = self.action.process

    @property
    def url(self):
        """The action's URL on the context."""
        return self.action.url(self.context)


class ProcessSharedUniqueProperty(SharedUniqueProperty):

    """Shared to-one resolved to the process of the referenced execution context."""
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        res = super(ProcessSharedUniqueProperty, self).__get__(obj, objtype)
        if res is not None:
            return res.process

        return None


class ProcessSharedMultipleProperty(SharedMultipleProperty):

    """Shared to-many resolved to the processes of the referenced execution contexts."""
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        res = super(ProcessSharedMultipleProperty, self).__get__(obj, objtype)
        return [e.process for e in res]


@implementer(IEntity)
class Entity(Object):

    """Collaboration object with state, actions and annotations."""
    creator = ProcessSharedUniqueProperty('creator', 'createds', True)
    involvers = ProcessSharedMultipleProperty('involvers', 'involveds', True)

    def __init__(self, **kwargs):
        super(Entity, self).__init__(**kwargs)
        self.state = PersistentList()
        self.__property__ = None

    def init_annotations(self):
        """Create the annotations BTree (``process_history`` lives here)."""
        self.annotations = OOBTree()

    @property
    def state_or_none(self):
        """The states, or ``[None]`` when empty (catalog convenience)."""
        return self.state if self.state else [None]

    @property
    def actions(self):
        """All applicable business actions, as ``ActionCall``s (catalog-driven)."""
        allactions = getAllBusinessAction(self)
        return [ActionCall(a, self) for a in allactions]

    def setstate(self, state):
        """Replace the state list (single value accepted)."""
        if not isinstance(state, (list, tuple)):
            state = [state]

        self.state = PersistentList(state)
