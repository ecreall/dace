# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi

"""The runtime service: the folder owning every process instance."""
from zope.interface import implementer

from substanced.interfaces import IService

from dace.interfaces import IRuntime
from dace.objectofcollaboration.entity import Entity
from dace.descriptors import CompositeMultipleProperty


@implementer(IRuntime, IService)
class Runtime(Entity):

    """Service folder of the process instances (``root['runtime']``)."""
    processes = CompositeMultipleProperty('processes', None, False)

    def getprocesses(self):
        """The owned process instances."""
        return self.processes
