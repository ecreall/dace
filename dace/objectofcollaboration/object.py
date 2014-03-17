from zope.interface import implements
import colander
from persistent.list import PersistentList

from substanced.folder import Folder

from dace.interfaces import INameChooser, IObject
from pontus.visual import VisualisableElement

# TODO a optimiser il faut, aussi, ajouter les relations de referensement
__compositunique__ = 'cu'


def CompositUniqueProperty(propertyref, opposite=None, isunique=False):

    key = propertyref+'_valuekey'
    
    def _get(self,):
        myproperty = self.__class__.properties[propertyref]
        if not hasattr(self, key):
            myproperty['init'](self)

        keyvalue = self.__dict__[key]
        if keyvalue is not None and keyvalue in self:
            return self[keyvalue]

        return None

    def _add(self, value, initiator=True):
        self.setproperty(propertyref, value)

    def _set(self, value, initiator=True):
        myproperty = self.__class__.properties[propertyref]
        if not hasattr(self, key):
            myproperty['init'](self)

        keyvalue = self.__dict__[key]
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
        if not hasattr(self, key):
            myproperty['init'](self)

        keyvalue = self.__dict__[key]
        if keyvalue is not None and self.__contains__(keyvalue) and self[keyvalue] == value:
            if initiator and opposite is not None:
                getattr(value, propertyref, None)['del'](value, self, False)

            self.remove(keyvalue)

    def init(self):
        if not hasattr(self, key):
            self.__dict__[key] = None

    return {'add':_add,
            'get':_get,
            'set':_set,
            'del':_del,
            'init': init,
            'data':{'name':propertyref,
                    'opposite': opposite,
                    'isunique': isunique,
                    'type':__compositunique__
                   }
           }


__compositmultiple__ = 'cm'


def CompositMultipleProperty(propertyref, opposite=None, isunique=False):
    keys = propertyref+'_contents_keys'

    def _get(self):
        myproperty = self.__class__.properties[propertyref]
        if not hasattr(self, keys):
            myproperty['init'](self)

        contents_keys = self.__dict__[keys]
        return [self[key] for key in contents_keys if key in self]

    def _add(self, value, initiator=True):
        if value is None:
            return

        myproperty = self.__class__.properties[propertyref]
        if not hasattr(self, keys):
            myproperty['init'](self)

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
        myproperty = self.__class__.properties[propertyref]
        if not hasattr(self, keys):
            myproperty['init'](self)

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
        if not hasattr(self, keys):
            self.__dict__[keys] = []

    return {'add':_add,
            'get':_get,
            'set':_set,
            'del':_del,
            'init': init,
            'data': {'name':propertyref,
                     'opposite': opposite,
                     'isunique': isunique,
                     'type':__compositmultiple__
                    }
           }


__properties__ = { __compositunique__: CompositUniqueProperty,
                   __compositmultiple__: CompositMultipleProperty}


class Object(VisualisableElement, Folder):

    implements(IObject)
    properties_def = {}
    template = 'pontus:templates/visualisable_templates/object.pt'

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, 'properties'):
            cls.properties = {}

        new_instance = super(Object, cls).__new__(cls, *args, **kwargs)
        new_instance.__init_proprties__()
        return new_instance

    def __init__(self, **kwargs):
        VisualisableElement.__init__(self, **kwargs)
        Folder.__init__(self)
        self.__property__ = None
        for _property in self.properties_def.keys():
            if kwargs.has_key(_property):
                self.setproperty(_property, kwargs[_property])
        
    def __init_proprties__(self):
        for p in self.properties_def.keys():
            op = __properties__[self.properties_def[p][0]]
            opposite = self.properties_def[p][1]
            isunique = self.properties_def[p][2]
            self.__addproperty__(op(p,opposite, isunique))

    def __addproperty__(self, _property, default=None):
        propertyref = _property['data']['name']
        if propertyref not in self.__class__.properties:

            self.__class__.properties[propertyref] = _property
            self.__class__.properties[propertyref]['init'](self)

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

    def get_data(self, node):
        result = {}
        for child in node:
            name = child.name
            val = getattr(self, name, colander.null)
            result[name] = val
        return result

    def set_data(self, appstruct):
        for name, val in appstruct.items():
            if hasattr(self, name):
                existing_val = getattr(self, name, None)
                new_val = appstruct[name]
                if existing_val != new_val:
                    setattr(self, name, new_val)

    def url(self, request, view=None, args=None):
        if view is None:
            #generalement c est la vue de l index associer qu'il faut retourner
            return request.mgmt_path(self, '@@index')
        else:
            return request.mgmt_path(self, '@@'+view)
