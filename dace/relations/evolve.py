import logging
import transaction

from substanced.util import find_catalogs
from . import get_relations_container

log = logging.getLogger('substanced')


def unindex_relations_from_other_catalogs(root, registry):
    log.info('Unindexing relations from other catalogs...')
    catalogs = find_catalogs(root)
    container = get_relations_container(root)
    for catalog in catalogs:
        for oid in container:
            catalog.unindex_resource(int(oid))

    transaction.commit()
    log.info('Unindexed %s relations from other catalogs.', len(container))
