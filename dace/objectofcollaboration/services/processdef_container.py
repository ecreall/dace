from pyramid.threadlocal import get_current_request, get_current_registry
from zope.interface import implements, providedBy, implementedBy
from persistent.list import PersistentList
from zope.interface import alsoProvides
import venusian

from substanced.folder import Folder
from substanced.interfaces import IService

from dace.interfaces import IProcessDefinitionContainer, IProcessDefinition
from ..entity import Entity
from ..object import COMPOSITE_MULTIPLE

DEFINITIONS = {}

class process_definition(object):

    def __init__(self, name, provides=None, direct=False, **kw):
       self.name = name
       self.provides = provides
       self.direct = direct
       self.kw = kw

    def __call__(self, wrapped):
        def callback(scanner, name, ob):
            provides = self.provides
            if self.direct:
                component = ob
                if self.provides is None:
                    provides = list(implementedBy(component))[0]
            else:
                component = ob(**self.kw)
                if self.provides is None:
                    provides = list(providedBy(component))[0]

            scanner.config.registry.registerUtility(component, provides, self.name)
            component._init_definition()
            DEFINITIONS[component.id] = component

        venusian.attach(wrapped, callback)
        return wrapped


def create_process_definition_container(root):
    def_container = ProcessDefinitionContainer()
    root['process_definition_container'] = def_container
    for definition in DEFINITIONS.values():
        definition.__name__ = definition.id
        def_container.add_definition(definition)

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


