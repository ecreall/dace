from zope.interface import Interface, Declaration, implements, providedBy
from pyramid.threadlocal import get_current_registry
from substanced.catalog import (
    catalog_factory,
    Field,
    Keyword,
    indexview,
    indexview_defaults,
    )
from substanced.util import get_oid

from dace.util import Adapter, adapter
from dace.interfaces import (
    IBusinessAction, IStartWorkItem, IDecisionWorkItem, IWorkItem)


class IObjectProvides(Interface):

    def object_provides():
        pass


class ISearchableObject(Interface):

    def process_id():
        pass

    def node_id():
        pass

    def process_inst_uid():
        pass

    def context_id():
        pass


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


@catalog_factory('dace')
class DaceIndexes(object):

    object_provides = Keyword()
    process_id = Field()
    node_id = Field()
    process_inst_uid = Keyword()
    context_id = Keyword()


@adapter(context=Interface)
class SearchableObject(Adapter):
    """Return provided interfaces of the object.
    """
    implements(IObjectProvides)

    def object_provides(self):
        return [i.__identifier__ for i in providedBy(self.context).flattened()]


@adapter(context=IStartWorkItem)
class StartWorkItemSearch(Adapter):
    implements(ISearchableObject)

    def process_id(self):
        return self.context.process_id

    def node_id(self):
        return self.context.node_id

    def process_inst_uid(self):
        return ()

    def context_id(self):
        return [i.__identifier__ for a in self.context.actions
                for i in Declaration(a.context).flattened()]


@adapter(context=IDecisionWorkItem)
class DecisionWorkItemSearch(Adapter):
    implements(ISearchableObject)

    def process_id(self):
        return self.context.process_id

    def node_id(self):
        return self.context.node_id

    def process_inst_uid(self):
        return [get_oid(self.context.__parent__.__parent__, None)]

    def context_id(self):
        return [i.__identifier__ for a in self.context.actions
                for i in Declaration(a.context).flattened()]


@adapter(context=IWorkItem)
class WorkItemSearch(Adapter):
    implements(ISearchableObject)

    def process_id(self):
        return self.context.process_id

    def node_id(self):
        return self.context.node_id

    def process_inst_uid(self):
        return [get_oid(self.context.__parent__.__parent__, None)]

    def context_id(self):
        return [i.__identifier__ for a in self.context.actions
                for i in Declaration(a.context).flattened()]


@adapter(context=IBusinessAction)
class BusinessActionSearch(Adapter):
    implements(ISearchableObject)

    def process_id(self):
        return self.context.process_id

    def node_id(self):
        return self.context.node_id

    def process_inst_uid(self):
        return [get_oid(self.context.__parent__.__parent__, None)]

    def context_id(self):
        return [i.__identifier__ for i in Declaration(self.context.context).flattened()]
