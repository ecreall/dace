from zope.interface import Interface, Declaration, implements, providedBy
from pyramid.threadlocal import get_current_registry
from substanced.util import get_oid
from substanced.root import Root
from substanced.catalog import (
    catalog_factory,
    Field,
    Keyword,
    indexview,
    indexview_defaults,
    )
from dace.util import Adapter, adapter
from dace.interfaces import (
    IBusinessAction, IStartWorkItem, IDecisionWorkItem, IWorkItem)
from dace.catalog.interfaces import IObjectProvides, ISearchableObject


@indexview_defaults(catalog_name='dace')
class DaceCatalogViews(object):
    def __init__(self, resource):
        self.resource = resource

    @indexview()
    def object_provides(self, default):
        adapter = get_current_registry().queryAdapter(self.resource, IObjectProvides)
        if adapter is None:
            return default

        return adapter.object_provides()

    @indexview()
    def object_type(self, default):
        adapter = get_current_registry().queryAdapter(self.resource, IObjectProvides)
        if adapter is None:
            return default

        return adapter.object_type()

    @indexview()
    def container_oid(self, default):
        adapter = get_current_registry().queryAdapter(self.resource, IObjectProvides)
        if adapter is None:
            return default

        return adapter.container_oid()

    @indexview()
    def containers_oids(self, default):
        adapter = get_current_registry().queryAdapter(self.resource, IObjectProvides)
        if adapter is None:
            return default

        return adapter.containers_oids()

    @indexview()
    def oid(self, default):
        adapter = get_current_registry().queryAdapter(self.resource, IObjectProvides)
        if adapter is None:
            return default

        return adapter.oid()

    @indexview()
    def process_id(self, default):
        adapter = get_current_registry().queryAdapter(self.resource, ISearchableObject)
        if adapter is None:
            return default

        return adapter.process_id()

    @indexview()
    def node_id(self, default):
        adapter = get_current_registry().queryAdapter(self.resource, ISearchableObject)
        if adapter is None:
            return default

        return adapter.node_id()

    @indexview()
    def process_inst_uid(self, default):
        adapter = get_current_registry().queryAdapter(self.resource, ISearchableObject)
        if adapter is None:
            return default

        return adapter.process_inst_uid()

    @indexview()
    def context_id(self, default):
        adapter = get_current_registry().queryAdapter(self.resource, ISearchableObject)
        if adapter is None:
            return default

        return adapter.context_id()

    @indexview()
    def context_provides(self, default):
        adapter = get_current_registry().queryAdapter(self.resource, ISearchableObject)
        if adapter is None:
            return default

        return adapter.context_provides()

    @indexview()
    def isautomatic(self, default):
        adapter = get_current_registry().queryAdapter(self.resource, ISearchableObject)
        if adapter is None:
            return default

        return adapter.isautomatic()


@catalog_factory('dace')
class DaceIndexes(object):

    object_provides = Keyword()
    object_type = Field()
    container_oid = Field()
    containers_oids = Keyword()
    oid = Field()
    process_id = Field()
    node_id = Field()
    process_inst_uid = Keyword()
    context_id = Keyword()
    context_provides = Keyword()
    isautomatic = Field()


@adapter(context=Interface)
class SearchableObject(Adapter):
    """Return provided interfaces of the object.
    """
    implements(IObjectProvides)

    def object_provides(self):
        return [i.__identifier__ for i in providedBy(self.context).flattened()]

    def object_type(self):
        if providedBy(self.context).declared:
            return providedBy(self.context).declared[0].__identifier__

        return ''

    def containers_oids(self):
        if type(self.context) == Root:
            return [-1]

        if getattr(self.context, '__parent__' , None) is None:
            return [-1]

        return self._get_oids(self.context.__parent__)

    def container_oid(self):
        if type(self.context) == Root:
            return -1

        if getattr(self.context, '__parent__' , None) is None:
            return 0

        if getattr(self.context.__parent__, '__parent__' , None) is None:
            return 0

        return get_oid(self.context.__parent__, None)

    def oid(self):
        return get_oid(self.context)

    def _get_oids(self, obj):
        result = []
        if getattr(obj, '__parent__' , None) is None:
            return [0]

        result.append(get_oid(obj, None))
        result.extend(self._get_oids(obj.__parent__))
        return result


@adapter(context=IStartWorkItem)
class StartWorkItemSearch(Adapter):
    implements(ISearchableObject)

    def process_id(self):
        return self.context.process_id

    def node_id(self):
        return self.context.node_id

    def process_inst_uid(self):
        return ()

    def context_provides(self):
        return [i.__identifier__ for a in self.context.actions
                for i in Declaration(a.context).flattened()]

    def context_id(self):
        return [a.context.__identifier__ for a in self.context.actions]

    def isautomatic(self):
        for a in self.context.actions:
            if a.isautomatic:
                return True

        return False


@adapter(context=IDecisionWorkItem)
class DecisionWorkItemSearch(Adapter):
    implements(ISearchableObject)

    def process_id(self):
        return self.context.process_id

    def node_id(self):
        return self.context.node_id

    def process_inst_uid(self):
        return [get_oid(self.context.__parent__.__parent__, None)]

    def context_provides(self):
        return [i.__identifier__ for a in self.context.actions
                for i in Declaration(a.context).flattened()]

    def context_id(self):
        return [a.context.__identifier__ for a in self.context.actions]

    def isautomatic(self):
        for a in self.context.actions:
            if a.isautomatic:
                return True

        return False


@adapter(context=IWorkItem)
class WorkItemSearch(Adapter):
    implements(ISearchableObject)

    def process_id(self):
        return self.context.process_id

    def node_id(self):
        return self.context.node_id

    def process_inst_uid(self):
        return [get_oid(self.context.__parent__.__parent__, None)]

    def context_provides(self):
        return [i.__identifier__ for a in self.context.actions
                for i in Declaration(a.context).flattened()]

    def context_id(self):
        return [a.context.__identifier__ for a in self.context.actions]

    def isautomatic(self):
        for a in self.context.actions:
            if a.isautomatic:
                return True

        return False


@adapter(context=IBusinessAction)
class BusinessActionSearch(Adapter):
    implements(ISearchableObject)

    def process_id(self):
        return self.context.process_id

    def node_id(self):
        return self.context.node_id

    def process_inst_uid(self):
        return [get_oid(self.context.__parent__.__parent__, None)]

    def context_provides(self):
        return [i.__identifier__ for i in Declaration(self.context.context).flattened()]

    def context_id(self):
        return [self.context.context.__identifier__]

    def isautomatic(self):
        return self.context.isautomatic
