from pyramid.threadlocal import get_current_request, get_current_registry
from zope.interface import implements
from persistent.list import PersistentList
from zope.interface import alsoProvides

from substanced.folder import Folder
from substanced.interfaces import IService

from dace.interfaces import IProcessDefinitionContainer, IProcessDefinition
from ..entity import Entity
from ..object import COMPOSITE_MULTIPLE

DEFINITIONS = {}

def create_process_definition_container(root):
    def_container = ProcessDefinitionContainer()
    root['process_definition_container'] = def_container
    registry = get_current_registry()
    for definition in DEFINITIONS.values():
        def_container.add_definition(definition)
        registry.registerUtility(definition, provided=IProcessDefinition, name=definition.id)

    alsoProvides(def_container, IService)


class ProcessDefinitionContainer(Entity):
    implements(IProcessDefinitionContainer, IService)

    properties_def = {'definitions': (COMPOSITE_MULTIPLE, None, False)}

    def __init__(self, **kwargs):
        super(ProcessDefinitionContainer, self).__init__(**kwargs)

    def getdefinitions(self):
        return self.processes

    @property
    def definitions(self):
        return self.getproperty('definitions')

    def add_definition(self, definition):
        self.addtoproperty('definitions', definition)


