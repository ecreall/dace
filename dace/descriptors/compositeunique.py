# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi, Vincent Fretin

from dace.descriptors import Descriptor

_marker = object()


class CompositeUniqueProperty(Descriptor):
    
    def __init__(self, propertyref='', opposite=None, isunique=False):
        self.propertyref = propertyref
        self.opposite = opposite
        self.isunique = isunique
        self.key = '_' + propertyref + '_value'

    def _get(self, obj):
        current_value_name = obj.__dict__.get(self.key, None)
        if current_value_name is not None:
            return obj.get(current_value_name, None)

        return None

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        return self._get(obj)

    def add(self, obj, value, initiator=True, moving=None):
        self.__set__(obj, value, initiator, moving)

    def __set__(self, obj, value, initiator=True, moving=None):
        self.init(obj)

        current_value_name = obj.__dict__[self.key]
        current_value = self._get(obj)
        if current_value_name is not None and current_value == value:
            return

        if current_value_name is not None:
            self.remove(obj, current_value)

        if value is None:
            # we already removed the old value, nothing to do
            return

        value_name = value.__name__
        value_parent = getattr(value, '__parent__', None)
        value_property = getattr(value, '__property__', None)
        moved_to = (((moving is not None) and obj) or None)
        #if the parent is a substanced container
        if not(None in (value_parent, value_property)):
            getattr(value_parent.__class__,
                    value_property).remove(
                        value_parent, value, True, moved_to)
        elif value_parent is not None:
            value_parent.remove(value_name, moving=moved_to)

        obj.add(value_name, value, moving=moving)
        value.__property__ = self.propertyref
        setattr(obj, self.key, value.__name__)
        if initiator and self.opposite is not None:
            opposite_property = getattr(value.__class__, self.opposite, _marker)
            if opposite_property is not _marker:
                opposite_property.add(value, obj, False)

    def remove(self, obj, value, initiator=True, moving=None):
        self.init(obj)
        current_value = self._get(obj)
        if current_value is not None and current_value == value:
            value_name = value.__name__
            if initiator and self.opposite is not None:
                opposite_property = getattr(value.__class__,
                                      self.opposite, _marker)
                if opposite_property is not _marker:
                    opposite_property.remove(value, obj, False)

            setattr(obj, self.key, None)
            value.__property__ = None
            obj.remove(value_name, moving=moving)

    def init(self, obj):
        if getattr(obj, self.key, _marker) is _marker:
            setattr(obj, self.key, None)
