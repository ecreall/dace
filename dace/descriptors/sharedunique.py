# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi, Vincent Fretin

from dace.descriptors import Descriptor, is_removed


_marker = object()


class SharedUniqueProperty(Descriptor):
    
    def __init__(self, propertyref='', opposite=None, isunique=False):
        self.propertyref = propertyref
        self.opposite = opposite
        self.isunique = isunique
        self.key = '_' + propertyref + '_value'

    def _remove_deprecated(self, obj):
        value = obj.__dict__.get(self.key, None)
        if is_removed(value):
            setattr(obj, self.key, None)

    def _get(self, obj):
        self._remove_deprecated(obj)
        return obj.__dict__.get(self.key, None)
        
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        return self._get(obj)

    def add(self, obj, value, initiator=True, moving=None):
        self.__set__(obj, value, initiator)

    def __set__(self, obj, value, initiator=True, moving=None):
        self.init(obj)
        current_value = self._get(obj)
        if current_value is not None and current_value == value:
            return

        if initiator and self.opposite is not None:
            opposite_property = getattr(value.__class__, self.opposite, _marker)
            if opposite_property is not _marker:
                opposite_property.add(value, obj, False)

        if current_value is not None:
            self.remove(obj, current_value)

        setattr(obj, self.key, value)

    def remove(self, obj, value, initiator=True, moving=None):
        self.init(obj)
        current_value = self._get(obj)
        if current_value is not None and current_value == value:
            if initiator and self.opposite is not None:
                opposite_property = getattr(value.__class__,
                                      self.opposite, _marker)
                if opposite_property is not _marker:
                    opposite_property.remove(value, obj, False)

            setattr(obj, self.key, None)

    def init(self, obj):
        if getattr(obj, self.key, _marker) is _marker:
            setattr(obj, self.key, None)
