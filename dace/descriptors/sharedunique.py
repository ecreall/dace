# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi, Vincent Fretin

"""Shared (reference) to-one relation descriptor.

Stores a ``ResourceRef`` under ``_<propertyref>_value`` on the holder;
maintains the ``opposite`` end automatically; replacing a value first
detaches the previous one.
"""
from dace.descriptors.base import Descriptor, ref, get_ref


_marker = object()


class SharedUniqueProperty(Descriptor):
    
    """To-one reference with automatic opposite maintenance."""
    def __init__(self, propertyref='', opposite=None, isunique=False):
        self.propertyref = propertyref
        self.opposite = opposite
        self.isunique = isunique
        self.key = '_' + propertyref + '_value'

    def _get(self, obj):
        """Resolve the stored reference (or ``None``)."""
        return get_ref(obj.__dict__.get(self.key, None))
        
    def __get__(self, obj, objtype=None):
        """Descriptor read: the referenced object, or the descriptor on the class."""
        if obj is None:
            return self

        return self._get(obj)

    def add(self, obj, value, initiator=True, moving=None):
        """Alias of ``__set__`` (uniform API with the multiple descriptors)."""
        self.__set__(obj, value, initiator)

    def __set__(self, obj, value, initiator=True, moving=None):
        """Set the reference, wiring the opposite end and detaching the previous value."""
        self.init(obj)
        current_value = self._get(obj)
        if current_value and current_value == value:
            return

        if initiator and self.opposite:
            opposite_property = getattr(value.__class__, self.opposite, _marker)
            if opposite_property is not _marker:
                opposite_property.add(value, obj, False)

        if current_value:
            self.remove(obj, current_value)

        setattr(obj, self.key, ref(value))

    def remove(self, obj, value, initiator=True, moving=None):
        """Clear the reference when it matches ``value`` (unwiring the opposite)."""
        self.init(obj)
        current_value = self._get(obj)
        if current_value and current_value == value:
            if initiator and self.opposite:
                opposite_property = getattr(value.__class__,
                                      self.opposite, _marker)
                if opposite_property is not _marker:
                    opposite_property.remove(value, obj, False)

            setattr(obj, self.key, None)

    def init(self, obj):
        """Ensure the storage slot exists."""
        if getattr(obj, self.key, _marker) is _marker:
            setattr(obj, self.key, None)
