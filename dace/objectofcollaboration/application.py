# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi

from zope.interface import implementer
from substanced.root import Root

from dace.objectofcollaboration.entity import Entity
from dace.interfaces import IApplication


@implementer(IApplication)
class Application(Entity, Root):

    def __init__(self, **kwargs):
        super(Application, self).__init__(**kwargs)
