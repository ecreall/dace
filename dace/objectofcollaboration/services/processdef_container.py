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
        definition.__name__ = definition.id
        self.addtoproperty('definitions', definition)

    def get_definition(self, name):
        definitions = dict([(d.id, d) for d in self.definitions])
        if name in definitions:
            return definitions[name]

        return None


class process_definition(object):

    def __init__(self, name, direct=False, **kw):
       self.name = name
       self.direct = direct
       self.kw = kw

    def __call__(self, wrapped):
        def callback(scanner, name, ob):
            if self.direct:
                component = ob
            else:
                component = ob(**self.kw)
                component._init_definition()

            try:
                db = scanner.config.registry._zodb_databases['']
                def_container = db.open().root()['app_root']['process_definition_container']
                old_def = def_container.get_definition(component.id)
                if old_def is not None:
                    def_container.delproperty('definitions', old_def)

                def_container.add_definition(component)
                import transaction
                transaction.commit()
            except Exception :
                DEFINITIONS[component.id] = component

        venusian.attach(wrapped, callback)
        return wrapped


def create_process_definition_container(root):
    def_container = ProcessDefinitionContainer(title='Process Definitions')
    root['process_definition_container'] = def_container
    for definition in DEFINITIONS.values():
        def_container.add_definition(definition)
