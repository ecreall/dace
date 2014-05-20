from zope.interface import implementer

from substanced.interfaces import IService

from dace.interfaces import IRuntime
from .entity import Entity
from .object import COMPOSITE_MULTIPLE


@implementer(IRuntime, IService)
class Runtime(Entity):

    properties_def = {'processes': (COMPOSITE_MULTIPLE, None, False)}

    def __init__(self, **kwargs):
        super(Runtime, self).__init__(**kwargs)

    def getprocesses(self):
        return self.processes

    @property
    def processes(self):
        return self.getproperty('processes')
