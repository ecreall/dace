from dace.descriptors import Descriptor

_marker = object()


class CompositeUniqueProperty(Descriptor):
    def __init__(self, propertyref='', opposite=None, isunique=False):
        self.propertyref = propertyref
        self.opposite = opposite
        self.isunique = isunique
        self.key = '_'+propertyref + '_value'

    def _get(self, obj):
        current_value_name = obj.__dict__.get(self.key, None)
        if current_value_name is not None:
            return obj[current_value_name]

        return None

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        return self._get(obj)

    def add(self, obj, value, initiator=True):
        self.__set__(obj, value, initiator)

    def __set__(self, obj, value, initiator=True):
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
        if getattr(value, '__property__', None) is not None:
            getattr(value.__parent__.__class__, value.__property__).remove(value.__parent__, value)
        elif getattr(value, '__parent__', None) is not None:
            value.__parent__.remove(value_name)

        obj.add(value_name, value)
        value.__property__ = self.propertyref
        setattr(obj, self.key, value.__name__)
        if initiator and self.opposite is not None:
            opposite_property = getattr(value.__class__, self.opposite, _marker)
            if opposite_property is not _marker:
                opposite_property.add(value, obj, False)

    def remove(self, obj, value, initiator=True):
        self.init(obj)
        value_name = value.__name__
        current_value = self._get(obj)
        if current_value is not None and current_value == value:
            if initiator and self.opposite is not None:
                opposite_property = getattr(value.__class__, self.opposite, _marker)
                if opposite_property is not _marker:
                    opposite_property.remove(value, obj, False)

            setattr(obj, self.key, None)
            obj.remove(value_name)

    def init(self, obj):
        if getattr(obj, self.key, _marker) is _marker:
            setattr(obj, self.key, None)
