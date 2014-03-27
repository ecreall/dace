from zope.interface import implements
from persistent.list import PersistentList

from substanced.folder import Folder

from dace.interfaces import IRuntime
from .entity import Entity
from .object import COMPOSITE_MULTIPLE


class Runtime(Entity):
    implements(IRuntime)

    properties_def = {'processes':(COMPOSITE_MULTIPLE, None, False)}

    def __init__(self, **kwargs):
        super(Runtime, self).__init__(**kwargs)


    def getprocesses(self):
        return self.processes

    @property
    def processes(self):
        return self.getproperty('processes')

