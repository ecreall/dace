# -*- coding: utf-8 -*-
from pyramid.events import subscriber
from pyramid.threadlocal import get_current_registry, get_current_request

from substanced.event import RootAdded

from dace.interfaces import IProcessDefinition
from dace.util import find_service
from .interfaces import IProcessDefinitionAdded
from .processdef_container import create_process_definition_container, DEFINITIONS


@subscriber(RootAdded)
def add_process_definition_container(event):
    root = event.object
    create_process_definition_container(root)


@subscriber(IProcessDefinitionAdded)
def add_process_def(event):
    definition = event.object
    definition._init_definition()
    registry.registerUtility(definition, provided=IProcessDefinition, name=definition.id)


def add_definition(definition):
    DEFINITIONS[definition.id] = definition


