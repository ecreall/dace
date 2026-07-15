# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi

"""The process-definition service.

Definitions declared with ``@process_definition`` land in the module
constant ``DEFINITIONS`` at scan time; the startup subscriber and the
evolve step synchronise them into
``root['process_definition_container']``.
"""
from zope.interface import implementer
import venusian

from substanced.interfaces import IService

from dace.interfaces import IProcessDefinitionContainer
from ..entity import Entity
from dace.descriptors import CompositeMultipleProperty


DEFINITIONS = {}


@implementer(IProcessDefinitionContainer, IService)
class ProcessDefinitionContainer(Entity):

    """Service folder holding the synchronised process definitions."""
    definitions = CompositeMultipleProperty('definitions', None, False)

    def __init__(self, **kwargs):
        super(ProcessDefinitionContainer, self).__init__(**kwargs)

    def add_definition(self, definition):
        """Adopt a definition (named by its id) and run its ``_init_definition``."""
        definition.__name__ = definition.id
        self.addtoproperty('definitions', definition)
        definition._init_definition()

    def get_definition(self, name):
        # Don't iterate on self.definitions property for performance reason.
        """Definition by id (direct folder access, not the property)."""
        return self.get(name, None)


class process_definition(object):

    """Venusian decorator registering a definition (instance) into ``DEFINITIONS``."""
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
