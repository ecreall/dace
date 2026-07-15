# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Vincent Fretin, Amen Souissi

"""The 'dace' hypatia catalog.

Eighteen indexes over two adapter contracts: ``IObjectProvides``
(interfaces, type, states, title/description, containment oids) served
by the default ``SearchableObject`` adapter for any object, and
``ISearchableObject`` (process id/discriminator, node id, instance
uid, context interfaces, automatic/system flags, potential contexts)
served by dedicated adapters for work-items, business actions and
processes. This is the machinery behind ``getAllBusinessAction`` and
every discovery query of ``dace.util``.
"""
from zope.interface import Interface, Declaration, implementer, providedBy
from pyramid.threadlocal import get_current_registry
from substanced.util import get_oid
from substanced.root import Root
from substanced.catalog import (
    catalog_factory,
    Field,
    Keyword,
    indexview,
    indexview_defaults,
    Text
    )
from dace.util import Adapter, adapter
from dace.interfaces import (
    IBusinessAction, IStartWorkItem, IDecisionWorkItem, IWorkItem, IProcess)
from dace.catalog.interfaces import IObjectProvides, ISearchableObject


@indexview_defaults(catalog_name='dace')
class DaceCatalogViews(object):
    """The 'dace' catalog index views: every index delegates to the
    resource's ``IObjectProvides`` (identity/containment) or
    ``ISearchableObject`` (process vocabulary) adapter — falling back to
    ``default`` when the resource has no adapter.
    """
    def __init__(self, resource):
        self.resource = resource

    @indexview()
    def object_provides(self, default):
        """Index view 'object_provides': delegated to the resource's adapter."""
        adapter = get_current_registry().queryAdapter(self.resource, IObjectProvides)
        if adapter is None:
            return default

        return adapter.object_provides()

    @indexview()
    def object_title(self, default):
        """Index view 'object_title': delegated to the resource's adapter."""
        adapter = get_current_registry().queryAdapter(self.resource, IObjectProvides)
        if adapter is None:
            return default

        return adapter.object_title()

    @indexview()
    def object_states(self, default):
        """Index view 'object_states': delegated to the resource's adapter."""
        adapter = get_current_registry().queryAdapter(self.resource, IObjectProvides)
        if adapter is None:
            return default

        return adapter.object_states()

    @indexview()
    def object_description(self, default):
        """Index view 'object_description': delegated to the resource's adapter."""
        adapter = get_current_registry().queryAdapter(self.resource, IObjectProvides)
        if adapter is None:
            return default

        return adapter.object_description()

    @indexview()
    def object_type(self, default):
        """Index view 'object_type': delegated to the resource's adapter."""
        adapter = get_current_registry().queryAdapter(self.resource, IObjectProvides)
        if adapter is None:
            return default

        return adapter.object_type()

    @indexview()
    def object_type_class(self, default):
        """Index view 'object_type_class': delegated to the resource's adapter."""
        adapter = get_current_registry().queryAdapter(self.resource, IObjectProvides)
        if adapter is None:
            return default

        return adapter.object_type_class()

    @indexview()
    def container_oid(self, default):
        """Index view 'container_oid': delegated to the resource's adapter."""
        adapter = get_current_registry().queryAdapter(self.resource, IObjectProvides)
        if adapter is None:
            return default

        return adapter.container_oid()

    @indexview()
    def containers_oids(self, default):
        """Index view 'containers_oids': delegated to the resource's adapter."""
        adapter = get_current_registry().queryAdapter(self.resource, IObjectProvides)
        if adapter is None:
            return default

        return adapter.containers_oids()

    @indexview()
    def oid(self, default):
        """Index view 'oid': delegated to the resource's adapter."""
        adapter = get_current_registry().queryAdapter(self.resource, IObjectProvides)
        if adapter is None:
            return default

        return adapter.oid()

    @indexview()
    def process_id(self, default):
        """Index view 'process_id': delegated to the resource's adapter."""
        adapter = get_current_registry().queryAdapter(self.resource, ISearchableObject)
        if adapter is None:
            return default

        return adapter.process_id()

    @indexview()
    def process_discriminator(self, default):
        """Index view 'process_discriminator': delegated to the resource's adapter."""
        adapter = get_current_registry().queryAdapter(self.resource, ISearchableObject)
        if adapter is None:
            return default

        return adapter.process_discriminator()

    @indexview()
    def node_id(self, default):
        """Index view 'node_id': delegated to the resource's adapter."""
        adapter = get_current_registry().queryAdapter(self.resource, ISearchableObject)
        if adapter is None:
            return default

        return adapter.node_id()

    @indexview()
    def process_inst_uid(self, default):
        """Index view 'process_inst_uid': delegated to the resource's adapter."""
        adapter = get_current_registry().queryAdapter(self.resource, ISearchableObject)
        if adapter is None:
            return default

        return adapter.process_inst_uid()

    @indexview()
    def context_id(self, default):
        """Index view 'context_id': delegated to the resource's adapter."""
        adapter = get_current_registry().queryAdapter(self.resource, ISearchableObject)
        if adapter is None:
            return default

        return adapter.context_id()

    @indexview()
    def context_provides(self, default):
        """Index view 'context_provides': delegated to the resource's adapter."""
        adapter = get_current_registry().queryAdapter(self.resource, ISearchableObject)
        if adapter is None:
            return default

        return adapter.context_provides()

    @indexview()
    def isautomatic(self, default):
        """Index view 'isautomatic': delegated to the resource's adapter."""
        adapter = get_current_registry().queryAdapter(self.resource, ISearchableObject)
        if adapter is None:
            return default

        return adapter.isautomatic()

    @indexview()
    def issystem(self, default):
        """Index view 'issystem': delegated to the resource's adapter."""
        adapter = get_current_registry().queryAdapter(self.resource, ISearchableObject)
        if adapter is None:
            return default

        return adapter.issystem()

    @indexview()
    def potential_contexts_ids(self, default):
        """Index view 'potential_contexts_ids': delegated to the resource's adapter."""
        adapter = get_current_registry().queryAdapter(self.resource, ISearchableObject)
        if adapter is None:
            return default

        return adapter.potential_contexts_ids()


@catalog_factory('dace')
class DaceIndexes(object):

    """Declaration of the 18 indexes of the dace catalog."""
    object_provides = Keyword()
    object_type = Field()
    object_type_class = Field()
    object_title = Text()
    object_states = Keyword()
    object_description = Text()
    container_oid = Field()
    containers_oids = Keyword()
    oid = Field()
    process_id = Field()
    process_discriminator = Field()
    node_id = Field()
    process_inst_uid = Keyword()
    context_id = Keyword()
    context_provides = Keyword()
    isautomatic = Field()
    issystem = Field()
    potential_contexts_ids = Keyword()


@adapter(context=Interface)
@implementer(IObjectProvides)
class SearchableObject(Adapter):
    """Return provided interfaces of the object.
    """

    def object_provides(self):
        """Identifiers of every provided interface (flattened)."""
        return [i.__identifier__ for i in providedBy(self.context).flattened()]

    def object_title(self):
        """The object's title."""
        return getattr(self.context, 'title', '')

    def object_description(self):
        """The object's description."""
        return getattr(self.context, 'description', '')

    def object_states(self):
        """Lowercased states (['none'] when stateless)."""
        states = list(getattr(self.context, 'state', []))
        if not states:
            return ['none']

        return [s.lower() for s in states]

    def object_type(self):
        """Identifier of the first declared interface."""
        if providedBy(self.context).declared:
            return providedBy(self.context).declared[0].__identifier__

        return ''

    def object_type_class(self):
        """The class name (used by the ``action_type`` filters)."""
        return self.context.__class__.__name__

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
@implementer(ISearchableObject)
class StartWorkItemSearch(Adapter):

    """Process vocabulary of a *virtual* start work-item (its actions rule automatic/system)."""
    def process_id(self):
        return self.context.process_id

    def process_discriminator(self):
        return self.context.process.discriminator

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

    def issystem(self):
        for action in self.context.actions:
            if action.issystem:
                return True

        return False

    def potential_contexts_ids(self):
        result = []
        for action in self.context.actions:
            result.extend(action.potential_contexts_ids)

        return list(set(result))


@adapter(context=IDecisionWorkItem)
@implementer(ISearchableObject)
class DecisionWorkItemSearch(Adapter):

    """Process vocabulary of a decision work-item."""
    def process_id(self):
        return self.context.process_id

    def process_discriminator(self):
        return self.context.process.discriminator

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
        for action in self.context.actions:
            if action.isautomatic:
                return True

        return False

    def issystem(self):
        for a in self.context.actions:
            if a.issystem:
                return True

        return False

    def potential_contexts_ids(self):
        result = []
        for action in self.context.actions:
            result.extend(action.potential_contexts_ids)

        return list(set(result))


@adapter(context=IWorkItem)
@implementer(ISearchableObject)
class WorkItemSearch(Adapter):

    """Process vocabulary of a concrete work-item."""
    def process_id(self):
        return self.context.process_id

    def process_discriminator(self):
        return self.context.process.discriminator

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
        for action in self.context.actions:
            if action.isautomatic:
                return True

        return False

    def issystem(self):
        for action in self.context.actions:
            if action.issystem:
                return True

        return False

    def potential_contexts_ids(self):
        result = []
        for action in self.context.actions:
            result.extend(action.potential_contexts_ids)

        return list(set(result))


@adapter(context=IBusinessAction)
@implementer(ISearchableObject)
class BusinessActionSearch(Adapter):

    """Process vocabulary of a business action (incl. its ``potential_contexts_ids``)."""
    def process_id(self):
        return self.context.process_id

    def process_discriminator(self):
        return self.context.process.discriminator

    def node_id(self):
        return self.context.node_id

    def process_inst_uid(self):
        return [get_oid(self.context.__parent__.__parent__, None)]

    def context_provides(self):
        return [i.__identifier__ \
                for i in Declaration(self.context.context).flattened()]

    def context_id(self):
        return [self.context.context.__identifier__]

    def isautomatic(self):
        return self.context.isautomatic

    def issystem(self):
        return self.context.issystem

    def potential_contexts_ids(self):
        return self.context.potential_contexts_ids


@adapter(context=IProcess)
@implementer(ISearchableObject)
class ProcessSearch(Adapter):

    """Process vocabulary of a process instance."""
    def process_id(self):
        return self.context.id

    def process_discriminator(self):
        return self.context.discriminator

    def node_id(self):
        return ''

    def process_inst_uid(self):
        return [get_oid(self.context, None)]

    def context_provides(self):
        return []

    def context_id(self):
        return []

    def isautomatic(self):
        return False

    def issystem(self):
        return False

    def potential_contexts_ids(self):
        return []