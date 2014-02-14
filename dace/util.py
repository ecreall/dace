from pyramid.threadlocal import get_current_request
from substanced.util import find_objectmap


def get_obj(oid):
    request = get_current_request()
    objectmap = find_objectmap(request.root)
    obj = objectmap.object_for(oid)
    return obj
