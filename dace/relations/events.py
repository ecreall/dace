# -*- coding: utf-8 -*-
from substanced.event import ObjectAdded, ObjectRemoved
from zope.interface import implements
from zope.interface.interfaces import ObjectEvent

from .interfaces import (
    IRelationAdded,
    IRelationDeleted,
    IRelationModified,
    IRelationSourceDeleted,
    IRelationTargetDeleted)


class RelationAdded(ObjectAdded):
    implements(IRelationAdded)


class RelationDeleted(ObjectRemoved):
    implements(IRelationDeleted)


class RelationModified(ObjectEvent):
    implements(IRelationModified)


class RelationSourceDeleted(ObjectEvent):
    implements(IRelationSourceDeleted)

    def __init__(self, object, relation):
        self.object = object
        self.relation = relation


class RelationTargetDeleted(ObjectEvent):
    implements(IRelationTargetDeleted)

    def __init__(self, object, relation):
        self.object = object
        self.relation = relation
