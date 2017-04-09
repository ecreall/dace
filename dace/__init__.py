# Copyright (c) 2014 by Ecreall under licence AGPL terms
# avalaible on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Vincent Fretin, Amen Souissi

import logging
from pyramid.i18n import TranslationStringFactory
from pyramid.threadlocal import get_current_request
from substanced.objectmap import find_objectmap
from zope.interface.interfaces import ComponentLookupError

from dace.relations.evolve import unindex_relations_from_other_catalogs

log = logging.getLogger('dace')
_ =  TranslationStringFactory('dace')


def process_definitions_evolve(root, registry):
    request = get_current_request()
    request.root = root  # needed when executing the step via sd_evolve script
    from dace.objectofcollaboration.services import processdef_container
    def_container = root['process_definition_container']
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
            def_container.delfromproperty('definitions', old_def)
            def_container.add_definition(definition)

    processdef_container.DEFINITIONS.clear()
    log.info('process definitions evolved. You absolutely need to restart the application to fix the node_definition attributes on context classes')
    # always run update catalogs and reindex after that
    update_catalogs_evolve(root, registry)


def update_catalogs_evolve(root, registry):
    # code taken from substanced/catalog/subscribers.py:on_startup
    request = get_current_request()
    request.root = root  # needed when executing the step via sd_evolve script
    objectmap = find_objectmap(root)
    if objectmap is not None:
        content = registry.content
        factory_type = content.factory_type_for_content_type('Catalog')
        oids = objectmap.get_extent(factory_type)
        for oid in oids:
            catalog = objectmap.object_for(oid)
            if catalog is not None:
                try:
                    catalog.update_indexes(
                        registry=registry,
                        reindex=True
                        )
                except ComponentLookupError:
                    # could not find a catalog factory
                    pass

    log.info('catalogs updated and new indexes reindexed')


def include_evolve_steps(config):
    config.add_evolution_step(process_definitions_evolve)
    config.add_evolution_step(update_catalogs_evolve)
    config.add_evolution_step(unindex_relations_from_other_catalogs)


def includeme(config):
    config.scan()
    config.include('.system')
    include_evolve_steps(config)
#    config.add_request_method(user, reify=True)
