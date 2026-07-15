# -*- coding: utf-8 -*-
# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Vincent Fretin, Amen Souissi

"""Concrete relation events (see ``interfaces``).

The ``Source``/``TargetDeleted`` pair carries the relation being
cascade-deleted with the object.
"""
from zope.interface import implementer
from zope.interface.interfaces import ObjectEvent

from .interfaces import (
    IRelationAdded,
    IRelationDeleted,
    IRelationModified,
    IRelationSourceDeleted,
    IRelationTargetDeleted)


@implementer(IRelationAdded)
class RelationAdded(ObjectEvent):
    """A relation was stored."""
    pass


@implementer(IRelationDeleted)
class RelationDeleted(ObjectEvent):
    """A relation was removed."""
    pass


@implementer(IRelationModified)
class RelationModified(ObjectEvent):
    """A relation was modified."""
    pass


@implementer(IRelationSourceDeleted)
class RelationSourceDeleted(ObjectEvent):

    """The source of ``relation`` was deleted (cascade in progress)."""
    def __init__(self, object, relation):
        self.object = object
        self.relation = relation


@implementer(IRelationTargetDeleted)
class RelationTargetDeleted(ObjectEvent):

    """The target of ``relation`` was deleted (cascade in progress)."""
    def __init__(self, object, relation):
        self.object = object
        self.relation = relation
