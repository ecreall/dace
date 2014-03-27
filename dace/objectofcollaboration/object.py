from zope.interface import implements
import colander
from persistent.list import PersistentList

from substanced.folder import Folder
from substanced.util import get_oid

from dace.interfaces import INameChooser, IObject
from dace.relations import connect, disconnect, find_relations
from pontus.visual import VisualisableElement

# TODO a optimiser il faut, aussi, ajouter les relations de referensement
COMPOSITE_UNIQUE = 'cu'


def CompositeUniqueProperty(propertyref, opposite=None, isunique=False):

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
        currentvalue = myproperty['get'](self)
        if keyvalue is not None and currentvalue == value:
            return

        if initiator and opposite is not None:
            value.__class__.properties[opposite]['add'](value, self, False)

        if keyvalue is not None:
            myproperty['del'](self, currentvalue)

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
                value.__class__.properties[opposite]['del'](value, self, False)

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
                    'type':COMPOSITE_UNIQUE
                   }
           }


COMPOSITE_MULTIPLE = 'cm'


def CompositeMultipleProperty(propertyref, opposite=None, isunique=False):
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
            value.__class__.properties[opposite]['add'](value, self, False)

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
                v.__class__.properties[opposite]['del'](v, self, False)

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
                     'type':COMPOSITE_MULTIPLE
                    }
           }


SHARED_UNIQUE = 'su'


def SharedUniqueProperty(propertyref, opposite=None, isunique=False):

    def _get(self,):
        opts = {u'source_id': get_oid(self)}
        opts[u'relation_id'] = propertyref
        try:
            return [r for r in find_relations(opts).all()][0].target
        except Exception:
            return None

    def _add(self, value, initiator=True):
        self.setproperty(propertyref, value)

    def _set(self, value, initiator=True):
        myproperty = self.__class__.properties[propertyref]
        currentvalue = myproperty['get'](self) 
        if currentvalue == value:
            return

        if initiator and opposite is not None:
            value.__class__.properties[opposite]['add'](value, self, False)

        myproperty['del'](self, currentvalue)
        if value is None:
            return
        kw = {}
        kw['relation_id'] = propertyref
        connect(self, value, **kw)

    def _del(self, value, initiator=True):
        myproperty = self.__class__.properties[propertyref]
        currentvalue = myproperty['get'](self) 
        if currentvalue is not None and currentvalue == value:
            if initiator and opposite is not None:
                value.__class__.properties[opposite]['del'](value, self, False)

            opts = {u'target_id': get_oid(value)}
            opts[u'relation_id'] = propertyref
            relation = [r for r in find_relations(opts).all()][0]
            disconnect(relation)

    def init(self):
        return

    return {'add':_add,
            'get':_get,
            'set':_set,
            'del':_del,
            'init': init,
            'data':{'name':propertyref,
                    'opposite': opposite,
                    'isunique': isunique,
                    'type':SHARED_UNIQUE
                   }
           }


SHARED_MULTIPLE = 'sm'

def SharedMultipleProperty(propertyref, opposite=None, isunique=False):

    def _get(self):
        opts = {u'source_id': get_oid(self)}
        opts[u'relation_id'] = propertyref
        try:
            return [r for r in find_relations(opts).all()]
        except Exception:
            return None

    def _add(self, value, initiator=True):
        if value is None:
            return

        myproperty = self.__class__.properties[propertyref]
        currentvalue = myproperty['get'](self) 
        if isunique and value in currentvalue:
            return

        if initiator and opposite is not None:
            value.__class__.properties[opposite]['add'](value, self, False)

        myproperty['del'](self, currentvalue)
        kw = {}
        kw['relation_id'] = propertyref           
        connect(self, value, **kw)

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
        if not isinstance(value, (list, tuple)):
            value = [value]

        for v in value:
            if initiator and opposite is not None:
                v.__class__.properties[opposite]['del'](v, self, False)

            opts = {u'target_id': get_oid(v)}
            opts[u'relation_id'] = propertyref
            relation = [r for r in find_relations(opts).all()][0]
            disconnect(relation)

    def init(self):
        return

    return {'add':_add,
            'get':_get,
            'set':_set,
            'del':_del,
            'init': init,
            'data': {'name':propertyref,
                     'opposite': opposite,
                     'isunique': isunique,
                     'type':SHARED_MULTIPLE
                    }
           }


__properties__ = { COMPOSITE_UNIQUE: CompositeUniqueProperty,
                   SHARED_UNIQUE: SharedUniqueProperty,
                   COMPOSITE_MULTIPLE: CompositeMultipleProperty,
                   SHARED_MULTIPLE: SharedMultipleProperty }


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
