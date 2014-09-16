from persistent.list import PersistentList

from dace.descriptors import Descriptor

_marker = object()


class SharedMultipleProperty(Descriptor):
    def __init__(self, propertyref='', opposite=None, isunique=False):
        self.propertyref = propertyref
        self.opposite = opposite
        self.isunique = isunique
        self.key = '_'+propertyref + '_value'

    def _get(self, obj):
        current_values = obj.__dict__.get(self.key, None)
        if current_values is not None:
            return current_values

        return []

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        return self._get(obj)

    def add(self, obj, value, initiator=True):
        if value is None:
            return

        self.init(obj)
        current_values = self._get(obj)
        if self.isunique and value in current_values:
            return

        if initiator and self.opposite is not None:
            opposite_property = getattr(value.__class__, self.opposite, _marker)
            if opposite_property is not _marker:
                opposite_property.add(value, obj, False)

        obj.__dict__[self.key].append(value)

    def __set__(self, obj, values, initiator=True):
        if not isinstance(values, (list, tuple, set)):
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
        for v in toadd:
            self.add(obj, v)

    def remove(self, obj, values, initiator=True):
        self.init(obj)
        relations = obj.__dict__[self.key]
        if not isinstance(values, (list, tuple, set)):
            values = [values]

        for value in values:
            if initiator and self.opposite is not None:
                opposite_property = getattr(value.__class__, self.opposite, _marker)
                if opposite_property is not _marker:
                    opposite_property.remove(value, obj, False)

            if value in relations:
                relations.remove(value)

    def init(self, obj):
        if getattr(obj, self.key, _marker) is _marker:
            setattr(obj, self.key, PersistentList())
