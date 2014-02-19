from zope.interface import Interface, Declaration
from pyramid.threadlocal import get_current_registry

from substanced.catalog import (
    catalog_factory,
    Text,
    Field,
    indexview,
    indexview_defaults,
    )
from dace.util import Adapter, adapter
 
from ..interfaces import (
        IEntity,
        IStartWorkItem,
        IDecisionWorkItem,
        IWorkItem)


class ISearchableWorkItem(Interface):
    def process_id():
        pass
    def node_id():
        pass
    def process_inst_uid():
        pass
    def context_id():
        pass

@indexview_defaults(catalog_name='searchableworkitem')
class SearchableWorkItemViews(object):
    def __init__(self, resource):
        self.resource = resource

    @indexview()
    def process_id(self, default):
        adapter = get_current_registry().queryAdapter(self.resource,ISearchableWorkItem)
        return adapter.process_id()

    @indexview()
    def node_id(self, default):
        adapter = get_current_registry().queryAdapter(self.resource,ISearchableWorkItem)
        return adapter.node_id()

    @indexview()
    def process_inst_uid(self, default):
        adapter = get_current_registry().queryAdapter(self.resource,ISearchableWorkItem)
        return adapter.process_inst_uid()

    @indexview()
    def context_id(self, default):
        adapter = get_current_registry().queryAdapter(self.resource,ISearchableWorkItem)
        return adapter.context_id()


@catalog_factory('searchableworkitem')
class SearchableWorkItem(object):
    #grok.context(ISearchableWorkItem)

    process_id = Field()
    node_id = Field()
    process_inst_uid = Keyword()
    context_id = Keyword()


@adapter(context = IStartWorkItem, name = u'startworkitemsearch' )
class StartWorkItemSearch(Adapter):
    grok.implements(ISearchableWorkItem)

    def process_id(self):
        return self.context.process_id

    def node_id(self):
        return self.context.node_id

    def process_inst_uid(self):
        return ()

    def context_id(self):
        return [i.__identifier__ for a in self.context.actions for i in Declaration(a.context).flattened()]


@adapter(context = IDecisionWorkItem, name = u'decisionworkitemsearch' )
class DecisionWorkItemSearch(Adapter):
    grok.implements(ISearchableWorkItem)

    def process_id(self):
        return self.context.process_id

    def node_id(self):
        return self.context.node_id

    def process_inst_uid(self):
        intids = getUtility(IIntIds)
        return [intids.queryId(self.context.__parent__.__parent__)]

    def context_id(self):
        return [i.__identifier__ for a in self.context.actions for i in Declaration(a.context).flattened()]


@adapter(context = IWorkItem, name = u'workitemsearch' )
class WorkItemSearch(Adapter):
    grok.implements(ISearchableWorkItem)

    def process_id(self):
        return self.context.process_id

    def node_id(self):
        return self.context.node_id

    def process_inst_uid(self):
        intids = getUtility(IIntIds)
        return [intids.queryId(self.context.__parent__.__parent__)]

    def context_id(self):
        return [i.__identifier__ for a in self.context.actions for i in Declaration(a.context).flattened()]