from zope.interface import implements

from .interfaces import IObject
from .entity import Entity


class Object(Entity):
    implements(IObject)
