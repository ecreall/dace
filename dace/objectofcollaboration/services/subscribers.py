# -*- coding: utf-8 -*-
# Copyright (c) 2014 by Ecreall under licence AGPL terms
# avalaible on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi

import os
from pyramid.events import ApplicationCreated, subscriber
from pyramid.settings import asbool
from pyramid.request import Request
from pyramid.threadlocal import get_current_request, manager
import transaction

from zope.processlifetime import DatabaseOpenedWithRoot
from substanced.event import RootAdded

from .processdef_container import ProcessDefinitionContainer
from . import processdef_container


@subscriber(RootAdded)
def add_process_definition_container(event):
    root = event.object
    if hasattr(root, 'reindex'):
        root.reindex()

    def_container = ProcessDefinitionContainer(title='Process Definitions')
    root['process_definition_container'] = def_container


@subscriber(ApplicationCreated)
def add_process_definitions(event):
    app = event.object
    registry = app.registry
    settings = getattr(registry, 'settings', {})
    request = Request.blank('/application_created') # path is meaningless
    request.registry = registry
    manager.push({'registry': registry, 'request': request})
    root = app.root_factory(request)
    request.root = root

    # use same env variable as substanced catalog to determine
    # if we want to recreate process definitions
    autosync = asbool(
        os.environ.get(
        'SUBSTANCED_CATALOGS_AUTOSYNC',
        settings.get(
            'substanced.catalogs.autosync',
            settings.get('substanced.autosync_catalogs', False) # bc
            )))
    def_container = root['process_definition_container']
    if autosync:
        for definition in def_container.definitions:
            if hasattr(definition, '_broken_object'):
                name = definition.__name__
                def_container.remove(name, send_events=False)
                def_container._definitions_value.remove(name)

    for definition in processdef_container.DEFINITIONS.values():
        old_def = def_container.get(definition.id, None)
        if old_def is None:
            def_container.add_definition(definition)
        else:
            if autosync:
                def_container.delfromproperty('definitions', old_def)
                def_container.add_definition(definition)

    for definition in def_container.definitions:
        for node in definition.nodes:
            for context in getattr(node, 'contexts', []):
                context.node_definition = node

    if autosync:
        processdef_container.DEFINITIONS.clear()

    transaction.commit()
    registry.notify(DatabaseOpenedWithRoot(root._p_jar.db()))
    manager.pop()
