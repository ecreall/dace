# -*- coding: utf-8 -*-
# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi


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

