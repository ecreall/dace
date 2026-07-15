# -*- coding: utf-8 -*-
# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author:  Vincent Fretin, Amen Souissi

"""The relation storage folder.

Adds/removes with ``send_events=False`` so ``RelationValue`` objects
never reach the ordinary content catalogs, and notifies the dedicated
``RelationAdded``/``RelationDeleted`` events instead.
"""
from zope.interface import implementer
from pyramid.threadlocal import get_current_registry
from substanced.folder import Folder
from substanced.interfaces import IService

from .events import RelationAdded, RelationDeleted

# send_events is False by default, to not index RelationValue in
# other catalogs

@implementer(IService)
class RelationsContainer(Folder):
    """A rough implementation of a relation storage.
    """

    def __setitem__(self, name, other):
        """Folder protocol: delegate to ``add`` (events off)."""
        return self.add(name, other, send_events=False)

    def add(self, name, other, send_events=False, reserved_names=(),
            duplicating=None, moving=None, loading=False, registry=None):
        """Store a relation silently, then notify ``RelationAdded``."""
        super(RelationsContainer, self).add(name, other,
            send_events=send_events, reserved_names=reserved_names,
            duplicating=duplicating, moving=moving, loading=loading,
            registry=registry)
        if registry is None:
            registry = get_current_registry()

        registry.notify(RelationAdded(other))

    def __delitem__(self, key):
        """Folder protocol: delegate to ``remove`` (events off)."""
        return self.remove(key, send_events=False)

    def remove(self, name, send_events=False, moving=None, loading=False,
               registry=None):
        """Notify ``RelationDeleted`` then remove silently (missing name: no-op)."""
        relation = self.get(name, None)
        if relation is not None:
            # If the name doesn't exists, nothing should happens. This
            # case can be triggered if you set a subscribers to
            # IRelationTargetDeletedEvent that end-up somehow deleting
            # the relation
            if registry is None:
                registry = get_current_registry()

            registry.notify(RelationDeleted(self.get(name)))
            super(RelationsContainer, self).remove(name,
                send_events=send_events, moving=moving, loading=loading,
                registry=registry)
        else:
            KeyError(name)
