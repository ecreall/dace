from zope.interface import implements
import colander

from .interfaces import IObject


class Object(object):
    implements(IObject)

    def __init__(self):
        super(Object, self).__init__()
        self.__property__ = None

    def get_data(self, node):
        result = {}
        for child in node:
            name = child.name
            val = getattr(self, name, colander.null)
            result[name] = val
        return result            
