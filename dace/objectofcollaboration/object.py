from zope.interface import implementer
from persistent.list import PersistentList
import colander
import datetime

from substanced.folder import Folder
from substanced.util import get_oid

from dace.interfaces import IObject
from dace.relations import connect, disconnect, find_relations

# TODO a optimiser il faut, aussi, ajouter les relations de referensement
COMPOSITE_UNIQUE = 'cu'

marker = object()

def CompositeUniqueProperty(propertyref, opposite=None, isunique=False):

    key = propertyref + '_valuekey'

    def _get(self):
        myproperty = self.__class__.properties[propertyref]
        if getattr(self, key, marker) is marker:
            myproperty['init'](self)

        keyvalue = getattr(self, key, None)
        if keyvalue is not None:
            return self.get(keyvalue, None)

        return None

    def _add(self, value, initiator=True):
        myproperty = self.__class__.properties[propertyref]
        myproperty['set'](self, value, initiator)

    def _set(self, value, initiator=True):
        myproperty = self.__class__.properties[propertyref]
        if not hasattr(self, key):
            myproperty['init'](self)

        keyvalue = getattr(self, key, None)
        currentvalue = myproperty['get'](self)
        if keyvalue is not None and currentvalue == value:
            return

        if keyvalue is not None:
            myproperty['del'](self, currentvalue)

        if value is None:
            setattr(self, key, None)
            return

        value_name = value.__name__
        if getattr(value, '__property__', None) is not None:
            value.__parent__.__class__.properties[value.__property__]['del'](value.__parent__, value)
        elif getattr(value, '__parent__', None) is not None:
            value.__parent__.remove(value_name)

        self.add(value_name, value)
        value.__property__ = propertyref
        setattr(self, key, value.__name__)
        if initiator and opposite is not None and opposite in value.__class__.properties:
            value.__class__.properties[opposite]['add'](value, self, False)

    def _del(self, value, initiator=True):
        myproperty = self.__class__.properties[propertyref]
        if getattr(self, key, marker) is marker:
            myproperty['init'](self)

        keyvalue = getattr(self, key, None)
        if keyvalue is not None and self.get(keyvalue, marker) == value:
            if initiator and opposite is not None and opposite in value.__class__.properties:
                value.__class__.properties[opposite]['del'](value, self, False)

            self.remove(keyvalue)

    def init(self):
        if getattr(self, key, marker) is marker:
            setattr(self, key, None)

    return {'add': _add,
            'get': _get,
            'set': _set,
            'del': _del,
            'init': init,
            'data': {'name': propertyref,
                     'opposite': opposite,
                     'isunique': isunique,
                     'type': COMPOSITE_UNIQUE
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
        value_name= value.__name__
        if getattr(value,'__property__', None) is not None:
            value.__parent__.__class__.properties[value.__property__]['del'](value.__parent__, value)
        elif hasattr(value,'__parent__') and value.__parent__ is not None:
            value.__parent__.remove(value_name)

        self.add(value_name, value)
        value.__property__ = propertyref
        contents_keys.append(value.__name__)
        setattr(self, keys, contents_keys)

        if initiator and opposite is not None and opposite in value.__class__.properties:
            value.__class__.properties[opposite]['add'](value, self, False)

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
            if initiator and opposite is not None and opposite in v.__class__.properties:
                v.__class__.properties[opposite]['del'](v, self, False)

            if self.__contains__(v.__name__):
                contents_keys.remove(v.__name__)
                self.remove(v.__name__)

    def init(self):
        if not hasattr(self, keys):
            setattr(self, keys, PersistentList())

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


def SharedUniquePropertyRelation(propertyref, opposite=None, isunique=False):

    def _get(self,):
        opts = {u'source_id': get_oid(self)}
        opts[u'relation_id'] = propertyref
        try:
            return [r for r in find_relations(self, opts).all()][0].target
        except Exception:
            return None

    def _add(self, value, initiator=True):
        myproperty = self.__class__.properties[propertyref]
        myproperty['set'](self, value, initiator)

    def _set(self, value, initiator=True):
        myproperty = self.__class__.properties[propertyref]
        currentvalue = myproperty['get'](self)
        if currentvalue == value:
            return

        if initiator and opposite is not None and opposite in value.__class__.properties:
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
            if initiator and opposite is not None and opposite in value.__class__.properties:
                value.__class__.properties[opposite]['del'](value, self, False)

            opts = {u'target_id': get_oid(value)}
            opts[u'relation_id'] = propertyref
            relation = [r for r in find_relations(self, opts).all()][0]
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

def SharedMultiplePropertyRelation(propertyref, opposite=None, isunique=False):

    def _get(self):
        opts = {u'source_id': get_oid(self)}
        opts[u'relation_id'] = propertyref
        try:
            return [r.target for r in find_relations(self, opts).all()]
        except Exception:
            return None

    def _add(self, value, initiator=True):
        if value is None:
            return

        myproperty = self.__class__.properties[propertyref]
        currentvalue = myproperty['get'](self)
        if isunique and value in currentvalue:
            return

        if initiator and opposite is not None and opposite in value.__class__.properties:
            value.__class__.properties[opposite]['add'](value, self, False)

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
        if not isinstance(value, (list, tuple)):
            value = [value]

        for v in value:
            if initiator and opposite is not None and opposite in v.__class__.properties:
                v.__class__.properties[opposite]['del'](v, self, False)

            opts = {u'target_id': get_oid(v)}
            opts[u'relation_id'] = propertyref
            relation = [r for r in find_relations(self, opts).all()][0]
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


def SharedUniqueProperty(propertyref, opposite=None, isunique=False):

    key = propertyref+'_value'

    def _get(self,):
        myproperty = self.__class__.properties[propertyref]
        if not hasattr(self, key):
            myproperty['init'](self)

        return self.__dict__[key]

    def _add(self, value, initiator=True):
        myproperty = self.__class__.properties[propertyref]
        myproperty['set'](self, value, initiator)

    def _set(self, value, initiator=True):
        myproperty = self.__class__.properties[propertyref]
        if not hasattr(self, key):
            myproperty['init'](self)

        currentvalue = myproperty['get'](self)
        if currentvalue == value:
            return

        if initiator and opposite is not None and opposite in value.__class__.properties:
            value.__class__.properties[opposite]['add'](value, self, False)

        myproperty['del'](self, currentvalue)
        if value is None:
            return

        setattr(self, key, value)

    def _del(self, value, initiator=True):
        myproperty = self.__class__.properties[propertyref]
        if not hasattr(self, key):
            myproperty['init'](self)

        currentvalue = myproperty['get'](self)
        if currentvalue is not None and currentvalue == value:
            if initiator and opposite is not None and opposite in value.__class__.properties:
                value.__class__.properties[opposite]['del'](value, self, False)

            setattr(self, key, None)

    def init(self):
        if not hasattr(self, key):
            setattr(self, key, None)

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


def SharedMultipleProperty(propertyref, opposite=None, isunique=False):

    key = propertyref+'_value'

    def _get(self):
        myproperty = self.__class__.properties[propertyref]
        if not hasattr(self, key):
            myproperty['init'](self)

        return self.__dict__[key]

    def _add(self, value, initiator=True):
        if value is None:
            return

        myproperty = self.__class__.properties[propertyref]
        if not hasattr(self, key):
            myproperty['init'](self)

        currentvalue = myproperty['get'](self)
        if isunique and value in currentvalue:
            return

        if initiator and opposite is not None and opposite in value.__class__.properties:
            value.__class__.properties[opposite]['add'](value, self, False)

        self.__dict__[key].append(value)

    def _set(self, value, initiator=True):
        myproperty = self.__class__.properties[propertyref]
        if not hasattr(self, key):
            myproperty['init'](self)

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
        if not hasattr(self, key):
            myproperty['init'](self)

        if not isinstance(value, (list, tuple)):
            value = [value]

        for v in value:
            if initiator and opposite is not None and opposite in v.__class__.properties:
                v.__class__.properties[opposite]['del'](v, self, False)

            if v in self.__dict__[key]:
                self.__dict__[key].remove(v)

    def init(self):
        if not hasattr(self, key):
            setattr(self, key, PersistentList())

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


__properties__ = {COMPOSITE_UNIQUE: CompositeUniqueProperty,
                  SHARED_UNIQUE: SharedUniqueProperty,
                  COMPOSITE_MULTIPLE: CompositeMultipleProperty,
                  SHARED_MULTIPLE: SharedMultipleProperty}


@implementer(IObject)
class Object(Folder):

    properties_def = {}
    dynamic_properties_reloaded = False

    def __new__(cls, *args, **kwargs):
        mro_cls = [c for c in cls.__mro__ if c is not cls and hasattr(c, 'properties_def')]
        for c in mro_cls:
            cls.properties_def.update(c.properties_def)

        if not hasattr(cls, 'properties'):
            cls.properties = {}

        new_instance = super(Object, cls).__new__(cls, *args, **kwargs)
        new_instance.__init_proprties__()
        return new_instance

    def __init__(self, **kwargs):
        super(Object, self).__init__()
        self.dynamic_properties_def = {}
        self.created_at = datetime.datetime.today()
        self.title = ''
        if 'title' in kwargs:
            self.title = kwargs['title']

        self.description = ''
        if 'description' in kwargs:
            self.description = kwargs['description']

        self.__property__ = None
        for _property in self.properties_def.keys():
            if _property in kwargs:
                self.setproperty(_property, kwargs[_property])
            else:
                self.__class__.properties[_property]['init'](self)

    def __init_proprties__(self):
        for name, propertydef in self.properties_def.items():
            self._init__property(name, propertydef)

    def _init_dynamic_properties_(self):
        self.dynamic_properties_reloaded = True
        for name, propertydef in self.dynamic_properties_def.items():
            self._init__property(name, propertydef)

    def _init__property(self, name, propertydef):
        if name not in self.__class__.properties:
            op = __properties__[propertydef[0]]
            opposite = propertydef[1]
            isunique = propertydef[2]
            self.__addproperty__(op(name,opposite, isunique))

    def __addproperty__(self, _property, default=None):
        propertyref = _property['data']['name']
        self.__class__.properties[propertyref] = _property
        self.__class__.properties[propertyref]['init'](self)
        if default is not None:
            _property['set'](self, default)

    def __setattr__(self, name, value):
        if name in self.__class__.properties:
            self.setproperty(name, value)
        else:
            super(Folder, self).__setattr__(name, value)

    def __getitem__(self, name):
        obj = super(Object, self).__getitem__(name)
        if hasattr(obj, 'dynamic_properties_def') and obj.dynamic_properties_def and not obj.dynamic_properties_reloaded:
            obj._init_dynamic_properties_()

        return obj

    def getproperty(self, name):
        return self.__class__.properties[name]['get'](self)

    def setproperty(self, name, value):
        self.__class__.properties[name]['set'](self, value)

    def addtoproperty(self, name, value):
        self.__class__.properties[name]['add'](self, value)

    def delproperty(self, name, value):
        self.__class__.properties[name]['del'](self, value)

    def choose_name(self, name, object):
        container = self.data

        # remove characters that checkName does not allow
        name = name.replace('/', '-').lstrip('+@')

        if not name:
            name = object.__class__.__name__
            if isinstance(name, bytes):
                name = name.decode()

        # for an existing name, append a number.
        # We should keep client's os.path.extsep (not ours), we assume it's '.'
        dot = name.rfind('.')
        if dot >= 0:
            suffix = name[dot:]
            name = name[:dot]
        else:
            suffix = ''

        n = name + suffix
        i = 1
        while n in container:
            i += 1
            n = name + u'-' + str(i) + suffix

        return n

    def add(self, name, other, send_events=True, reserved_names=(),
            duplicating=None, moving=None, loading=False, registry=None):
        name = self.choose_name(name, other)
        super(Object, self).add(name, other, send_events, reserved_names,
                duplicating, moving, loading, registry)

    def get_data(self, node):
        result = {}
        for child in node:
            name = child.name
            val = getattr(self, name, colander.null)
            result[name] = val
        return result

    def set_data(self, appstruct):
        for name, val in appstruct.items():
            # If a field was added to the form schema afterwards, the object won't have the attribute
            # and the value will not be set. TODO Check if name is in th content type schema?
            if hasattr(self, name):
                existing_val = getattr(self, name, None)
                new_val = appstruct[name]
                if existing_val != new_val:
                    setattr(self, name, new_val)

    # TODO: use something like this ?
    # def set_data(self, appstruct, omit=()):
    #     for name, val in appstruct.items():
    #         if name not in omit:
    #             existing_val = getattr(self, name, None)
    #             new_val = appstruct[name]
    #             if existing_val != new_val:
    #                 setattr(self, name, new_val)
