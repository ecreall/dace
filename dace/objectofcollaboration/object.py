
import datetime
from zope.interface import implementer
import colander
from pyramid.compat import is_nonstr_iter
from pyramid.threadlocal import get_current_registry

from substanced.folder import Folder
from substanced.event import ObjectModified

from dace.interfaces import IObject
from dace.descriptors import Descriptor, __properties__


_marker = object()


@implementer(IObject)
class Object(Folder):

    title = ''
    description = ''

    def __init__(self, **kwargs):
        super(Object, self).__init__()
        self.dynamic_properties_def = {}
        self.created_at = datetime.datetime.today()
        self.modified_at = datetime.datetime.today()
        if 'title' in kwargs:
            self.title = kwargs['title']

        if 'description' in kwargs:
            self.description = kwargs['description']

        self.__property__ = None
        for key, value in kwargs.items():
            descriptor = getattr(self.__class__, key, _marker)
            if descriptor is not _marker and isinstance(descriptor, Descriptor):
                descriptor.__set__(self, value)

    def getproperty(self, name):
        return getattr(self, name)

    def setproperty(self, name, value):
        setattr(self, name, value)

    def addtoproperty(self, name, value):
        getattr(self.__class__, name).add(self, value)

    def delproperty(self, name, value):
        getattr(self.__class__, name).remove(self, value)

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
        container = self.data

        # remove characters that checkName does not allow
        try:
            name = str(name)
        except:
            name = ''
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
