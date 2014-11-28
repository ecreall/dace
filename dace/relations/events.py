# -*- coding: utf-8 -*-
# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Vincent Fretin, Amen Souissi

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
    pass


@implementer(IRelationDeleted)
class RelationDeleted(ObjectEvent):
    pass


@implementer(IRelationModified)
class RelationModified(ObjectEvent):
    pass


@implementer(IRelationSourceDeleted)
class RelationSourceDeleted(ObjectEvent):

    def __init__(self, object, relation):
        self.object = object
        self.relation = relation


@implementer(IRelationTargetDeleted)
class RelationTargetDeleted(ObjectEvent):

    def __init__(self, object, relation):
        self.object = object
        self.relation = relation
