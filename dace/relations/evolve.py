"""Evolve step: remove relation oids from every non-relation catalog
(they were historically indexed everywhere; the container now adds
with events off).
"""
import logging
import transaction

from substanced.util import find_catalogs
from . import get_relations_container

log = logging.getLogger('substanced')


def unindex_relations_from_other_catalogs(root, registry):
    """Sweep every catalog and unindex each stored relation oid; commit."""
    log.info('Unindexing relations from other catalogs...')
    catalogs = find_catalogs(root)
    container = get_relations_container(root)
    for catalog in catalogs:
        for oid in container:
            catalog.unindex_resource(int(oid))

    transaction.commit()
    log.info('Unindexed %s relations from other catalogs.', len(container))
