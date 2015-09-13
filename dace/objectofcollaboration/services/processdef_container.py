# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi

from zope.interface import implementer
import venusian

from substanced.interfaces import IService

from dace.interfaces import IProcessDefinitionContainer
from ..entity import Entity
from dace.descriptors import CompositeMultipleProperty


DEFINITIONS = {}


@implementer(IProcessDefinitionContainer, IService)
class ProcessDefinitionContainer(Entity):

    definitions = CompositeMultipleProperty('definitions', None, False)

    def __init__(self, **kwargs):
        super(ProcessDefinitionContainer, self).__init__(**kwargs)

    def add_definition(self, definition):
        definition.__name__ = definition.id
        self.addtoproperty('definitions', definition)
        definition._init_definition()

    def get_definition(self, name):
        for definition in self.definitions:
            if definition.id == name:
                return definition

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

            DEFINITIONS[component.id] = component

        venusian.attach(wrapped, callback)
        return wrapped
