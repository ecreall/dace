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

    for definition in def_container.definitions:
        for node in definition.nodes:
            for context in getattr(node, 'contexts', []):
                context.node_definition = node

    import transaction
    transaction.commit()
    processdef_container.DEFINITIONS.clear()
    log.info('process definitions evolved.')


def includeme(config):
    config.scan()
    config.include('.system')
    config.add_evolution_step(process_definitions_evolve)
#    config.add_request_method(user, reify=True)
