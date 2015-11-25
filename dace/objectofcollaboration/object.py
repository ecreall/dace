# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi

import datetime
import pytz

from zope.interface import implementer
import colander
from pyramid.compat import is_nonstr_iter
from pyramid.threadlocal import get_current_registry

from substanced.folder import Folder
from substanced.event import ObjectModified

from dace.interfaces import IObject
from dace.util import name_chooser
from dace.descriptors import Descriptor, __properties__


_marker = object()


@implementer(IObject)
class Object(Folder):

    title = ''
    description = ''

    def __init__(self, **kwargs):
        super(Object, self).__init__()
        self.dynamic_properties_def = {}
        self.created_at = datetime.datetime.now(tz=pytz.UTC)
        self.modified_at = datetime.datetime.now(tz=pytz.UTC)
        if 'title' in kwargs:
            self.title = kwargs['title']

        if 'description' in kwargs:
            self.description = kwargs['description']

        self.__property__ = None
        for key, value in kwargs.items():
            descriptor = getattr(self.__class__, key, _marker)
            if descriptor is not _marker and isinstance(descriptor, Descriptor):
                descriptor.__set__(self, value)

    def __delitem__(self, name):
        """ Remove the object from this folder stored under ``name``.

        ``name`` must be a Unicode object or a bytestring object.

        If ``name`` is a bytestring object, it must be decodable using the
        system default encoding.

        If no object is stored in the folder under ``name``, raise a
        :exc:`KeyError`.
        """
        obj_property = getattr(self[name], '__property__', None)
        if obj_property:
            self.delfromproperty(obj_property, self[name])
        else:
            self.remove(name)

    def _init_property(self, name, propertydef):
        descriptor = getattr(self.__class__, name, _marker)
        if descriptor is _marker:
            op = __properties__[propertydef[0]]
            opposite = propertydef[1]
            isunique = propertydef[2]
            setattr(self.__class__, name, op(name, opposite, isunique))

    def __setstate__(self, state):
        super(Object, self).__setstate__(state)
        if not hasattr(self, 'dynamic_properties_def'):
            return

        for name, propertydef in self.dynamic_properties_def.items():
            self._init_property(name, propertydef)

    def choose_name(self, name, object):
        if not name:
            name = getattr(object, 'title', object.__class__.__name__)
            if not name:
                name = object.__class__.__name__

            if isinstance(name, bytes):
                name = name.decode()
                
        new_name = name_chooser(self.data, name)
        return new_name

    def add(self, name, other, send_events=True, reserved_names=(),
            duplicating=None, moving=None, loading=False, registry=None):
        name = self.choose_name(name, other)
        super(Object, self).add(name, other, send_events, reserved_names,
                duplicating, moving, loading, registry)

    def move(self, name, other, newname=None, registry=None):
        """
        Move a subobject named ``name`` from this folder to the folder
        represented by ``other``.  `other`` that represent a tuple 
        (the object target, property name). If ``newname`` is not none, it is used as
        the target object name; otherwise the existing subobject name is
        used.

        This operation is done in terms of a remove and an add.  The Removed
        and WillBeRemoved events as well as the Added and WillBeAdded events
        sent will indicate that the object is moving.
        """
        target = None
        property_name = None
        if isinstance(other, tuple):
            target = other[0]
            property_name = other[1]
        else:
            target = other

        if newname is None:
            newname = name
        if registry is None:
            registry = get_current_registry()

        objtomove = self[name]
        obj_property = getattr(self[name], '__property__', None)
        if not property_name and not obj_property:
            objtomove = super(Object, self).move(name, target, 
                                              newname, registry)
        elif property_name and obj_property:
            self.delfromproperty(obj_property, objtomove, target)
            objtomove.__name__ = newname
            target.addtoproperty(property_name, objtomove, self)
        elif not obj_property:
            objtomove.__name__ = newname
            target.addtoproperty(property_name, objtomove, self)
        elif not property_name:
            self.delfromproperty(obj_property, objtomove, target)
            target.add(newname, objtomove, moving=self, registry=registry)

        return objtomove

    def rename(self, oldname, newname, registry=None):
        """
        Rename a subobject from oldname to newname.

        This operation is done in terms of a remove and an add.  The Removed
        and WillBeRemoved events sent will indicate that the object is
        moving.
        """

        obj_property = getattr(self[oldname], '__property__', None)
        if obj_property:
            self.move(oldname, (self, obj_property), newname, registry)
        else:
            self.move(oldname, self, newname, registry)

    def set_data(self, appstruct, omit=('_csrf_token_', '__objectoid__')):
        if not is_nonstr_iter(omit):
            omit = (omit,)

        changed = False
        for name, val in appstruct.items():
            if name not in omit:
                existing_val = getattr(self, name, _marker)
                new_val = appstruct[name]
                if existing_val != new_val:
                    # avoid setting an attribute on the object if it's the same
                    # value as the existing value to avoid database bloat
                    setattr(self, name, new_val)
                    changed = True

        if changed:
            event = ObjectModified(self)
            registry = get_current_registry()
            registry.subscribers((event, self), None)

    def get_data(self, node, ignore_null=False):
        """return values of attributes descibed in
           the colander schema node 'node' """
        result = {}
        for child in node:
            name = child.name
            val = getattr(self, name, colander.null)
            if val is colander.null and ignore_null:
                continue

            result[name] = val

        return result

    def getproperty(self, name):
        return getattr(self, name)

    def setproperty(self, name, value):
        setattr(self, name, value)

    def addtoproperty(self, name, value, moving=None):
        getattr(self.__class__, name).add(self, value, moving=moving)

    def delfromproperty(self, name, value, moving=None):
        getattr(self.__class__, name).remove(self, value, moving=moving)

    def reindex(self):
        event = ObjectModified(self)
        registry = get_current_registry()
        registry.subscribers((event, self), None)
