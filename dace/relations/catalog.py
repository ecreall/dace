import BTrees
from substanced.util import find_objectmap, get_oid, set_oid
import zc.relation.catalog

from .interfaces import IRelationValue
from .container import RelationsContainer


_marker = object()


def dumpObject(obj, catalog, cache):
    objectid = get_oid(obj, _marker)

    if objectid is _marker:
        objectmap = cache.get('objectmap')
        if objectmap is None:
            objectmap = cache['objectmap'] = find_objectmap(catalog)
        objectid = objectmap.new_objectid()
        set_oid(obj, objectid)

    return objectid


def loadObject(token, catalog, cache):
    objectmap = cache.get('objectmap')
    if objectmap is None:
        objectmap = cache['objectmap'] = find_objectmap(catalog)
    return objectmap.object_for(token)


def create_catalog(root):
    catalog = zc.relation.catalog.Catalog(dumpObject, loadObject,
                                          btree=BTrees.family32.OI)
    catalog.addValueIndex(
        IRelationValue['source_id'])
    catalog.addValueIndex(
        IRelationValue['target_id'])
    catalog.addValueIndex(
        IRelationValue['state'],
        btree = BTrees.family32.OI)
    catalog.addValueIndex(
        IRelationValue['tags'],
        btree=BTrees.family32.OO,
        multiple=True,
        name='tag')
    catalog.addValueIndex(
        IRelationValue['from_interfaces_flattened'],
        multiple=True,
        btree=BTrees.family32.OI)
    catalog.addValueIndex(
        IRelationValue['to_interfaces_flattened'],
        multiple=True,
        btree=BTrees.family32.OI)
#    root['relations_catalog'] = catalog
#    root['relations_container'] = RelationsContainer()
    # TODO register relations catalog and container as a service
    # register as ICatalog local utility or use find_catalog('relations')
