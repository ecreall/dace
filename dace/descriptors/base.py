# Copyright (c) 2014 by Ecreall under licence AGPL terms
# avalaible on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi

from persistent.wref import WeakRef
from ZODB.POSException import POSKeyError


class Descriptor(object):
    pass


class ResourceRef(object):

    def __init__(self, resource):
        try:
            self.ref = WeakRef(resource)
        except Exception:
            self.ref = resource

    def __call__(self):
        if isinstance(self.ref, WeakRef):
            ref = self.ref()
            if ref is None:
                # The object is not in the database anymore.
                return None

            try:
                # If a zeopack occurred and the process was not restarted after
                # that, it's possible that WeakRef._v_ob is
                # a ghostified object and trying accessing the object will try
                # to wake it up and raise POSKeyError because the
                # object is not in the database anymore.
                name = getattr(ref, '__name__', None)
            except POSKeyError:
                delattr(self.ref, '_v_ob')
                return None

            if name is None:
                # If name is None, it means that the object is not in any
                # container meaning the user removed the object
                # but we can still access it from the db until
                # the filestorage is packed.
                # We want to return None in this case.
                return None

            return ref

        return self.ref

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
