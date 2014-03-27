from pyramid.threadlocal import get_current_request
from substanced.util import find_objectmap, set_oid

from .values import RelationValue


def get_relations_container():
    request = get_current_request()
    return request.root['relations_container']


def get_relations_catalog():
    request = get_current_request()
    return request.root.get('relations', None)


def find_relations(query):
    catalog = get_relations_catalog()
    request = get_current_request()
    objectmap = find_objectmap(request.root)
    queryobject = None
    for index, value in query.items():
        if isinstance(value, (tuple, list)):
            querytype = value[0]
            value = value[1]
        else:
            querytype = 'eq'

        criterion = getattr(catalog[index], querytype)(value)
        if queryobject is None:
            queryobject = criterion
        else:
            queryobject &= criterion

    resultset = queryobject.execute(resolver=objectmap.object_for)
    return resultset


def connect(source, target, **kwargs):
    container = get_relations_container()
    objectmap = find_objectmap(container)
    source_id, target_id = objectmap._refids_for(source, target)
    relation = RelationValue(source_id, target_id, **kwargs)
    objectid = objectmap.new_objectid()
    set_oid(relation, objectid)
    container[str(objectid)] = relation
    return relation


def disconnect(relation):
    parent = relation.__parent__
    del parent[relation.__name__]
