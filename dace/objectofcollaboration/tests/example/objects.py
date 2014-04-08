from zope.interface import implements

from dace.interfaces import IObject
from dace.objectofcollaboration.object import (
                COMPOSITE_UNIQUE, 
                SHARED_UNIQUE,
                COMPOSITE_MULTIPLE,
                SHARED_MULTIPLE,
                Object)

from dace.objectofcollaboration.entity import Entity


class Object1(Object):
    properties_def = {'composition_u':(COMPOSITE_UNIQUE, 'schared2_u', False),
                      'composition_m':(COMPOSITE_MULTIPLE, 'schared21_u', False),
                      'schared_u':(SHARED_UNIQUE, 'schared22_u', False),
                      'schared_m':(SHARED_MULTIPLE, 'schared23_u', False)}

    def __init__(self, **kwargs):
        Object.__init__(self, **kwargs)


class Object2(Object):
    properties_def = {'schared2_u':(SHARED_UNIQUE, 'composition_u', False),
                      'schared21_u':(SHARED_UNIQUE, 'composition_m', False),
                      'schared22_u':(SHARED_UNIQUE, 'schared_u', False),
                      'schared23_u':(SHARED_UNIQUE, 'schared_m', False)}

    def __init__(self, **kwargs):
        Object.__init__(self, **kwargs)


class IObjectA(IObject):
    pass


class IObjectB(IObject):
    pass


class IObjectC(IObjectB):
    pass


class ObjectA(Entity):
    implements(IObjectA)
    properties_def = {'composition_m':(COMPOSITE_MULTIPLE, None, False)}

    def __init__(self, **kwargs):
        Entity.__init__(self, **kwargs)


class ObjectB(Object):
    implements(IObjectB)

    def __init__(self, **kwargs):
        Object.__init__(self, **kwargs)


class ObjectC(ObjectB):
    implements(IObjectC)

    def __init__(self, **kwargs):
        ObjectB.__init__(self, **kwargs)
