from zope.interface import Interface, Declaration, implements, providedBy
from pyramid.threadlocal import get_current_registry
from zope.location.interfaces import ILocation

from substanced.catalog import (
    catalog_factory,
    Keyword,
    indexview,
    indexview_defaults,
    )

from dace.util import Adapter, adapter


class IObjectProvides(Interface):
    def object_provides():
        pass


@indexview_defaults(catalog_name='objectprovidesindexes')
class ObjectProvidesViews(object):
    def __init__(self, resource):
        self.resource = resource

    @indexview()
    def object_provides(self, default):
        adapter = get_current_registry().queryAdapter(self.resource,IObjectProvides)
        if adapter is None:
            return default
        return adapter.process_id()


@catalog_factory('objectprovidesindexes')
class ObjectProvidesIndexes(object):
    #grok.context(IObjectProvides)

    object_provides = Keyword()


@adapter(context = ILocation, name = u'objectprovides' )
class ObjectProvides(Adapter):
    """Return provided interfaces of the object.
    """
    implements(IObjectProvides)

    def object_provides(self):
        return [i.__identifier__ for i in providedBy(self.context).flattened()]
