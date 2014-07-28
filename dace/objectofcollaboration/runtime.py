from zope.interface import implementer

from substanced.interfaces import IService

from dace.interfaces import IRuntime
from .entity import Entity
from dace.descriptors import CompositeMultipleProperty


@implementer(IRuntime, IService)
class Runtime(Entity):

    processes = CompositeMultipleProperty('processes', None, False)

    def getprocesses(self):
        return self.processes
