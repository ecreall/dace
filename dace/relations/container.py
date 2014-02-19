# -*- coding: utf-8 -*-
from BTrees.OOBTree import OOBTree
from pyramid.threadlocal import get_current_registry
from pyramid.interfaces import ILocation
from zope.interface import implements, alsoProvides

from .events import RelationAdded, RelationDeleted
#from .interfaces import IRelationsContainer


class RelationsContainer(OOBTree):
    """A rough implementation of a relation storage.
    """
#    implements(IRelationsContainer)

    def __setitem__(self, key, value):
        value.__parent__ = self
        value.__name__ = key
        alsoProvides(value, ILocation)
        OOBTree.__setitem__(self, key, value)
        registry = get_current_registry()
        registry.notify(RelationAdded(value))

    def __delitem__(self, key):
        relation = self.get(key, None)
        if relation is not None:
            # If the key doesn't exists, nothing should happens. This
            # case can be triggered if you set a subscribers to
            # IRelationTargetDeletedEvent that end-up somehow deleting
            # the relation
            registry = get_current_registry()
            registry.notify(RelationDeleted(self.get(key)))
            OOBTree.__delitem__(self, key)
        else:
            KeyError(key)
