from zope.interface import implements

from .interfaces import IObject


class Object(object):
    implements(IObject)

    def __init__(self):
        super(Object, self).__init__()
        self.__property__ = None

