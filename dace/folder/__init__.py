from substanced.folder import Folder as FD
from persistent.list import PersistentList
from dace.interfaces import INameChooser
from dace.object import Object



def CompositUniqueProperty(propertyref, opposite=None, isunique=False):

    key = propertyref+'_valuekey'
    
    def _get(self,):
        keyvalue = getattr(self, key, None)
        if keyvalue is not None:
            return self[keyvalue]

        return None

    def _add(self, value, initiator=True):
        self.setproperty(propertyref, value)

    def _set(self, value, initiator=True):
        myproperty = self.__class__.properties[propertyref]
        keyvalue = getattr(self, key, None)
        if keyvalue is not None and myproperty['get'](self) == value:
            return

        if initiator and opposite is not None:
            getattr(value, opposite, None)['add'](value, self, False)

        if keyvalue is not None:
            myproperty['del'](self, myproperty['get'](self))

        if value is None:
            setattr(self, key, None)
            return            

        if getattr(value,'__property__', None) is not None:
            value.__parent__.__class__.properties[value.__property__]['del'](value.__parent__, value)
 
        name = INameChooser(self).chooseName(u'', value)
        self.add(name, value)
        value.__property__ = propertyref
        setattr(self, key, name)

    def _del(self, value, initiator=True):
        myproperty = self.__class__.properties[propertyref]
        keyvalue = getattr(self, key, None)
        if keyvalue is not None and myproperty['get'](self) == value:
            if initiator and opposite is not None:
                getattr(value, propertyref, None)['del'](value, self, False)

            self.remove(keyvalue)

    def init(self):
        self.__dict__[key] = None

    return {'add':_add, 'get':_get, 'set':_set, 'del':_del, 'init': init, 'name':propertyref}



def CompositMultipleProperty(propertyref, opposite=None, isunique=False):
    keys = propertyref+'_contents_keys'

    def _get(self):
        contents_keys = self.__dict__[keys]
        return [self[key] for key in contents_keys]

    def _add(self, value, initiator=True):
        myproperty = self.__class__.properties[propertyref]
        contents_keys = self.__dict__[keys]

        if isunique and value in myproperty['get'](self):
            return

        if initiator and opposite is not None:
            getattr(value, opposite, None)['add'](value, self, False)

        if getattr(value,'__property__', None) is not None:
            value.__parent__.__class__.properties[value.__property__]['del'](value.__parent__, value)

        name = INameChooser(self).chooseName(u'', value)
        self.add(name, value)
        value.__property__ = propertyref
        contents_keys.append(name)
        setattr(self, keys, contents_keys)

    def _set(self, value, initiator=True):
        
        myproperty = self.__class__.properties[propertyref]
        if not isinstance(value, (list, tuple)):
            value = [value]

        oldvalues = myproperty['get'](self)
        toremove = []
        toadd = []
        if value is None:
            toremove = oldvalues
        else:  
            toremove = [v for v in oldvalues if not (v in value)]
            toadd = [v for v in value if not (v in oldvalues)]

        myproperty['del'](self, toremove)
        if toadd:
            for v in toadd:
                myproperty['add'](self, v)

    def _del(self, value, initiator=True):
        contents_keys = self.__dict__[keys]
        if not isinstance(value, (list, tuple)):
            value = [value]

        for v in value:
            if initiator and opposite is not None:
                getattr(v, propertyref, None)['del'](v, self, False)

            if self.__contains__(v.name):
                contents_keys.remove(v.name)
                self.remove(v.name)

    def init(self):
        self.__dict__[keys] = []

    return {'add':_add, 'get':_get, 'set':_set, 'del':_del, 'init': init, 'name':propertyref}


class Folder(Object, FD):

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, 'properties'):
            cls.properties = {}

        new_instance = super(Folder, cls).__new__(cls, *args, **kwargs)
        return new_instance

    def __init__(self):
        Object.__init__(self)
        FD.__init__(self)

    def __addproperty__(self, _property, default=None):
        if _property['name'] not in self.__class__.properties:
            self.__class__.properties[_property['name']] = _property

        self.__class__.properties[_property['name']]['init'](self)
        if default is not None:
            _property['set'](self, default)

    def __setattr__(self, name, value):
        if name in self.__class__.properties:
            self.setproperty(name, value)
        else:
            super(Folder, self).__setattr__(name, value)

    def getproperty(self, name):
        return self.__class__.properties[name]['get'](self)

    def setproperty(self, name, value):
        self.__class__.properties[name]['set'](self, value)

    def addtoproperty(self, name, value):
        self.__class__.properties[name]['add'](self, value)
