# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi

from zope.interface import implementer

from substanced.interfaces import IService

from dace.interfaces import IRuntime
from dace.objectofcollaboration.entity import Entity
from dace.descriptors import CompositeMultipleProperty


@implementer(IRuntime, IService)
class Runtime(Entity):

    processes = CompositeMultipleProperty('processes', None, False)

    def getprocesses(self):
        return self.processes
