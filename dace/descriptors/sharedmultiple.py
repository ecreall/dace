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
        """Return a tuple (references, need_cleanup)

        need_cleanup is a boolean which indicate if there is a
        ResourceRef that evaluated to None and so can be removed.
        """
        references = list(obj.__dict__.get(self.key, []))
        values = list(filter(lambda x: x is not None,
                      [get_ref(o) for o in references]))
        return values, len(references) != len(values)

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        return self._get(obj)[0]

    def add(self, obj, value, initiator=True, moving=None):
        if value is None:
            return

        self.init(obj)
        current_values, need_cleanup = self._get(obj)
        if need_cleanup:
            self._cleanup(obj)

        if self.isunique and value in current_values:
            return

        if initiator and self.opposite:
            opposite_property = getattr(value.__class__, self.opposite, _marker)
            if opposite_property is not _marker:
                opposite_property.add(value, obj, False)

        obj.__dict__[self.key].append(ref(value))

    def _cleanup(self, obj):
        references = [o for o in obj.__dict__.get(self.key, [])
                      if get_ref(o) is not None]
        setattr(obj, self.key, PersistentList(references))

    def __set__(self, obj, values, initiator=True, moving=None):
        if not isinstance(values, (list, tuple, set, PersistentList)):
            values = [values]

        oldvalues, need_cleanup = self._get(obj)
        if need_cleanup:
            self._cleanup(obj)

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
