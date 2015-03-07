# Copyright (c) 2014 by Ecreall under licence AGPL terms
# avalaible on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi

from persistent.wref import WeakRef


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
            name = getattr(ref, '__name__', None)
            if name is not None:
                obj = ref
        else:
            obj = self.ref

        return obj

    def __hash__(self):
        self = self()
        # if self is None:
        #     raise TypeError('Weakly-referenced object has gone away')

        return hash(self)

    def __eq__(self, other):
        if not isinstance(other, ResourceRef):
            return False

        self = self()
        # if self is None:
        #     raise TypeError('Weakly-referenced object has gone away')

        other = other()
        # if other is None:
        #     raise TypeError('Weakly-referenced object has gone away')

        return self == other


def ref(resource):
    return ResourceRef(resource)


def get_ref(obj):
    if isinstance(obj, ResourceRef):
        return obj()
    else :
        return obj
