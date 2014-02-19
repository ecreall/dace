# -*- coding: utf-8 -*-
from substanced.interfaces import IObjectAdded, IObjectRemoved
from zc.relation.interfaces import ICatalog  # keep it
from zope.schema import Int, TextLine, List
from zope.interface import Interface, Attribute
from zope.interface.interfaces import IObjectEvent

from .. import _



class IRelationAdded(IObjectAdded):
    """A relation has been added.
    """


class IRelationDeleted(IObjectEvent):
    """A relation has been deleted.
    """


class IRelationModified(IObjectRemoved):
    """A relation has been modified.
    """


class IRelationSourceDeleted(IObjectEvent):
    """The source of a relation has been deleted.
    """
    relation = Attribute(u"Relation")


class IRelationTargetDeleted(IObjectEvent):
    """The target of a relation has been deleted.
    """
    relation = Attribute(u"Relation")


class IRelationValue(Interface):
    """A simple relation One to One.
    """
    source_id = Int(
        title = _(u"source_intid", default=u"Intid of the source object"),
        required = True,
        )
    target_id = Int(
        title = _(u"target_intid", default=u"Intid of the target object"),
        required = True,
        )
    source = Attribute("The source object of the relation.")
    target = Attribute("The target object of the relation.")
    state = TextLine(
        title = _(u"state", default=u"State of the relation"),
        required = True,
        default = u""
        )
    from_interfaces_flattened = Attribute(
        "Interfaces of the from object, flattened. "
        "This includes all base interfaces.")
    to_interfaces_flattened = Attribute(
        "The interfaces of the to object, flattened. "
        "This includes all base interfaces.")
    tags = List(
        title = _(u"tags", default=u"Tags of the relation"),
        required = True,
        default = [],
        value_type = TextLine()
        )
