from pyramid.threadlocal import get_current_request
from substanced.util import find_objectmap, set_oid
from zc.relation.catalog import any
from substanced.interfaces import ICatalog

from .values import RelationValue


def get_relations_container():
    request = get_current_request()
    root = request.root
    return root['relations_container']


def connect(source, target, **kwargs):
    container = get_relations_container()
    objectmap = find_objectmap(container)
    source_id, target_id = objectmap._refids_for(source, target)
    relation = RelationValue(source_id, target_id, **kwargs)
    objectid = objectmap.new_objectid()
    set_oid(relation, objectid)
    container[str(objectid)] = relation


#def includeme(config): # pragma: no cover
#    config.scan('.subscribers')
