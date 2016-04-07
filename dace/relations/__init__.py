# Copyright (c) 2014 by Ecreall under licence AGPL terms
# avalaible on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author:  Vincent Fretin, Amen Souissi

from pyramid.threadlocal import get_current_request
from substanced.util import find_objectmap, set_oid
from pyramid.traversal import find_root
from .values import RelationValue


# TODO def get_relations_container(root, query)
def get_relations_container(resource):
    root = find_root(resource)
    return root['relations_container']


# TODO get_relations_catalog(root, query)
def get_relations_catalog(resource):
    root = find_root(resource)
    return root.get('relations', None)


INTERSECTION_ORDER = ['relation_id', 'source_id', 'target_id']

def get_order(e):
    try:
        return INTERSECTION_ORDER.index(e[0])
    except ValueError:
        return 999

_marker = object()

class RequestMemojito(object):
    propname = '_memojito_'

    def invalidate_cache(self):
        request = get_current_request()
        if request:
            setattr(request, self.propname, dict())

    def request_memoize(self, func):

        def memogetter(*args, **kwargs):
            request = get_current_request()
            if not request:
                return func(*args, **kwargs)

            cache = getattr(request, self.propname, _marker)
            if cache is _marker:
                setattr(request, self.propname, dict())
                cache = getattr(request, self.propname)

            key = (func.__name__, tuple(sorted(args[1].items())))  # custom version that only works for find_relations below
            val = cache.get(key, _marker)
            if val is _marker:
                val = func(*args, **kwargs)
                cache[key] = val
                setattr(request, self.propname, cache)
            return val
        return memogetter


_m = RequestMemojito()
request_memoize = _m.request_memoize
invalidate_cache = _m.invalidate_cache

# TODO def find_relations(root, query)
@request_memoize
def find_relations(resource, query):
    catalog = get_relations_catalog(resource)
    root = find_root(resource)
    objectmap = find_objectmap(root)
    queryobject = None
    for index, value in sorted(query.items(), key=get_order):
        if 'reftype' == index: # ignore reftype, it's always 'Role'
            continue

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
    #print('%s %s'%(query, len(resultset)))
    return resultset


def connect(source, target, **kwargs):
    container = get_relations_container(source)
    objectmap = find_objectmap(container)
    source_id, target_id = objectmap._refids_for(source, target)
    relation = RelationValue(source_id, target_id, **kwargs)
    objectid = objectmap.new_objectid()
    set_oid(relation, objectid)
    container.add(str(objectid), relation, send_events=False)
    invalidate_cache()
    return relation


def disconnect(relation):
    parent = relation.__parent__
    parent.remove(relation.__name__, send_events=False)
    invalidate_cache()
