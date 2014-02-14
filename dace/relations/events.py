# -*- coding: utf-8 -*-
from substanced.event import ObjectAddedEvent, ObjectRemovedEvent
from zope.interface import implements
from zope.interface.interfaces import ObjectEvent

from .interfaces import (
    IRelationAddedEvent,
    IRelationDeletedEvent,
    IRelationModifiedEvent,
    IRelationSourceDeletedEvent,
    IRelationTargetDeletedEvent)


class RelationAddedEvent(ObjectAddedEvent):
    implements(IRelationAddedEvent)


class RelationDeletedEvent(ObjectRemovedEvent):
    implements(IRelationDeletedEvent)


class RelationModifiedEvent(ObjectEvent):
    implements(IRelationModifiedEvent)


class RelationSourceDeletedEvent(ObjectEvent):
    implements(IRelationSourceDeletedEvent)

    def __init__(self, object, relation):
        self.object = object
        self.relation = relation


class RelationTargetDeletedEvent(ObjectEvent):
    implements(IRelationTargetDeletedEvent)

    def __init__(self, object, relation):
        self.object = object
        self.relation = relation
