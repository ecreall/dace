# -*- coding: utf-8 -*-
from zope.interface import implementer
from pyramid.threadlocal import get_current_registry
from substanced.folder import Folder
from substanced.interfaces import IService

from .events import RelationAdded, RelationDeleted

@implementer(IService)
class RelationsContainer(Folder):
    """A rough implementation of a relation storage.
    """

    def __setitem__(self, key, value):
        super(RelationsContainer, self).__setitem__(key, value)
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
            super(RelationsContainer, self).__delitem__(key)
        else:
            KeyError(key)
