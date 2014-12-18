# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi

from persistent.wref import WeakRef
from pyramid.traversal import find_root
from pyramid.threadlocal import get_current_request

from substanced.util import get_oid, find_objectmap


class Descriptor(object):
    pass


class ResourceRef(object):

    def __init__(self, resource):
        try:
            self.ref = WeakRef(resource)
        except Exception:
            self.ref = resource

    def __call__(self):
        obj = None
        if isinstance(self.ref, WeakRef):
            ref = self.ref()
            oid = get_oid(ref, None)
            if oid:
                request = get_current_request()
                root = getattr(request, 'root', find_root(ref))
                objectmap = find_objectmap(root)
                obj = objectmap.object_for(oid)

        else :
            obj = self.ref

        return obj

    def __eq__(self, other):
        return isinstance(other, ResourceRef) and \
               other() is self.ref() 


def ref(resource):
    return ResourceRef(resource)


def get_ref(obj):
    if isinstance(obj, ResourceRef):
        return obj()
    else :
        return obj	
