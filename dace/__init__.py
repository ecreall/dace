# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Vincent Fretin, Amen Souissi

import logging
from pyramid.i18n import TranslationStringFactory

log = logging.getLogger('dace')
_ =  TranslationStringFactory('dace')


def process_definitions_evolve(root, registry):
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
    log.info('process definitions evolved.')


def utc_converter(root, registry):
    from dace.util import find_catalog
    from .interfaces import IObject
    import pytz
    dace_catalog = find_catalog('dace')
    object_provides_index = dace_catalog['object_provides']
    query = object_provides_index.any((IObject.__identifier__,))
    result = query.execute().all()
    for obj in result:
        obj.created_at = obj.created_at.replace(tzinfo=pytz.UTC)
        obj.modified_at = obj.modified_at.replace(tzinfo=pytz.UTC)
        obj.reindex()

    log.info('utc evolved.')


def includeme(config):
    config.scan()
    config.include('.system')
    config.add_evolution_step(process_definitions_evolve)
    config.add_evolution_step(utc_converter)
#    config.add_request_method(user, reify=True)
