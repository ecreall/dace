from pyramid.threadlocal import get_current_request, get_current_registry
import venusian

from substanced.util import find_objectmap, find_catalog as fcsd


class Adapter(object):

    def __init__(self, context):
        self.context = context


def get_obj(oid):
    request = get_current_request()
    objectmap = find_objectmap(request.root)
    obj = objectmap.object_for(oid)
    return obj


class utility(object):

    def __init__(self, name):
       self.name = name

    def __call__(self, wrapped):
        def callback(scanner, name, ob):
            instance = ob()
            get_current_registry().registerUtility(component=instance, name=self.name)

        venusian.attach(wrapped, callback)
        return wrapped


class adapter(object):

    def __init__(self, name, context):
       self.context = context
       self.name = name

    def __call__(self, wrapped):
        def callback(scanner, name, ob):
            mprovided = list(ob.__implemented__.interfaces())[0]
            get_current_registry().registerAdapter(factory=ob, required=(self.context,), provided=mprovided ,name=self.name)

        venusian.attach(wrapped, callback)
        return wrapped


def find_catalog(name=None):
    resource = get_current_request().root
    fcsd(resource, name)
