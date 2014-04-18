# -*- coding: utf-8 -*-
from zope.interface import Interface, Attribute
from zope.interface.interfaces import IObjectEvent


class IProcessDefinitionAdded(IObjectEvent):
    """A process def has been added.
    """


class IProcessDefinitionDeleted(IObjectEvent):
    """A process def has been deleted.
    """


class IProcessDefinitionModified(IObjectEvent):
    """A process def has been modified.
    """

