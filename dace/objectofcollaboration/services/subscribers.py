# -*- coding: utf-8 -*-
# Copyright (c) 2014 by Ecreall under licence AGPL terms
# avalaible on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi

import os
from pyramid.events import ApplicationCreated, subscriber
from pyramid.settings import asbool
from pyramid.request import Request
from pyramid.threadlocal import manager
import transaction

from ZODB.POSException import ConflictError
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
    def_container._initializing = True


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
    # if we want to recreate process definitions.
    # autosync is True only in development mode.
    autosync = asbool(
        os.environ.get(
        'SUBSTANCED_CATALOGS_AUTOSYNC',
        settings.get(
            'substanced.catalogs.autosync',
            settings.get('substanced.autosync_catalogs', False) # bc
            )))
    try:
        # This code block must be in sync with what we do in
        # process_definitions_evolve minus the autosync conditions
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
                # We add the definition at startup when creating the application
                # the first time where we normally have one worker.
                # If we have more that one worker, the other workers will do
                # a ConflictError here.
                if getattr(def_container, '_initializing', False) or autosync:
                    def_container.add_definition(definition)
            else:
                if autosync:
                    def_container.delfromproperty('definitions', old_def)
                    def_container.add_definition(definition)

        if autosync:
            # if not autosync, we still need this global constant for the
            # process_definitions_evolve step
            processdef_container.DEFINITIONS.clear()

        if getattr(def_container, '_initializing', False):
            del def_container._initializing

        transaction.commit()
    except ConflictError:
        # The first worker did the changes, simply abort to get the changes.
        transaction.abort()

    # After the restart of the application, we always need to resync
    # the node_definition attributes to be the node definition instances
    # currently in ZODB.
    for definition in def_container.definitions:
        for node in definition.nodes:
            for context in getattr(node, 'contexts', []):
                # context here is a class, we set the class attribute
                # node_definition to the current node definition in ZODB
                context.node_definition = node

    registry.notify(DatabaseOpenedWithRoot(root._p_jar.db()))
    manager.pop()
