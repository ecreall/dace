from zope.interface import Interface, Declaration

from substanced.catalog import (
    catalog_factory,
    Text,
    Field,
    )
from dace.util import Adapter, adapter
 
from ..interfaces import (
        IEntity,
        IStartWorkItem,
        IDecisionWorkItem,
        IWorkItem)


@catalog_factory('searchableworkitem')
class SearchableWorkItem(object):
    #grok.context(ISearchableWorkItem)

    process_id = Field()
    node_id = Field()
    process_inst_uid = Set()
    context_id = Set()


class ISearchableWorkItem(Interface):
    def process_id():
        pass
    def node_id():
        pass
    def process_inst_uid():
        pass
    def context_id():
        pass

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
