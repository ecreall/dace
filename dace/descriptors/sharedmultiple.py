# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi, Vincent Fretin

from persistent.list import PersistentList

from dace.descriptors.base import Descriptor, ref, get_ref


_marker = object()


class SharedMultipleProperty(Descriptor):
    
    def __init__(self, propertyref='', opposite=None, isunique=False):
        self.propertyref = propertyref
        self.opposite = opposite
        self.isunique = isunique
        self.key = '_' + propertyref + '_value'

    def _get(self, obj):
        return [get_ref(o) for o \
                in obj.__dict__.get(self.key, []) \
                if get_ref(o)]

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        return self._get(obj)

    def add(self, obj, value, initiator=True, moving=None):
        if value is None:
            return

        self.init(obj)
        current_values = self._get(obj)
        if self.isunique and value in current_values:
            return

        if initiator and self.opposite:
            opposite_property = getattr(value.__class__, self.opposite, _marker)
            if opposite_property is not _marker:
                opposite_property.add(value, obj, False)

        obj.__dict__[self.key].append(ref(value))

    def __set__(self, obj, values, initiator=True, moving=None):
        if not isinstance(values, (list, tuple, set, PersistentList)):
            values = [values]

        oldvalues = self._get(obj)
        toremove = []
        toadd = []
        if values is None:
            toremove = oldvalues
        else:
            toremove = [v for v in oldvalues if v not in values]
            toadd = [v for v in values if v not in oldvalues]

        self.remove(obj, toremove)
        for value_toadd in toadd:
            self.add(obj, value_toadd)

    def remove(self, obj, values, initiator=True, moving=None):
        self.init(obj)
        relations = obj.__dict__[self.key]
        if not isinstance(values, (list, tuple, set)):
            values = [values]

        for value in values:
            if initiator and self.opposite:
                opposite_property = getattr(value.__class__, 
                                       self.opposite, _marker)
                if opposite_property is not _marker:
                    opposite_property.remove(value, obj, False)

            value_ref = ref(value)
            if value_ref in relations:
                relations.remove(value_ref)
            elif value in relations:
                relations.remove(value)

    def init(self, obj):
        if getattr(obj, self.key, _marker) is _marker:
            setattr(obj, self.key, PersistentList())
