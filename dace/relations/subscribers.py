# -*- coding: utf-8 -*-
from pyramid.events import subscriber
from pyramid.threadlocal import get_current_registry
from substanced.event import RootAdded
from substanced.interfaces import IObjectWillBeRemovedEvent
from substanced.util import find_objectmap, get_oid, set_oid

from .interfaces import (
    ICatalog,
    IRelationAddedEvent,
    IRelationModifiedEvent,
    IRelationValue,
    )
from .catalog import create_catalog
from .events import RelationSourceDeletedEvent, RelationTargetDeletedEvent


@subscriber(RootAdded)
def add_relations_catalog(event):
    root = event.object
    create_catalog(root)


@subscriber(IRelationValue, IRelationModifiedEvent)
def update_relation(relation, event):
    registry = get_current_registry()
    catalog = registry.getUtility(ICatalog)
    catalog.unindex(relation)
    catalog.index_doc(get_oid(relation), relation)


@subscriber(IRelationValue, IRelationAddedEvent)
def add_relation(relation, event):
    registry = get_current_registry()
    catalog = registry.getUtility(ICatalog)
    objectmap = find_objectmap(relation)
    objectid = objectmap.new_objectid()
    set_oid(relation, objectid)
    catalog.index_doc(objectid, relation)


@subscriber(IObjectWillBeRemovedEvent)
def object_deleted(event):
    registry = get_current_registry()
    ob = event.object
    catalog = registry.queryUtility(ICatalog)
    if catalog is None:
        # We don't have a Catalog installed in this part of the site
        return

    if IRelationValue.providedBy(ob):
        # We assume relations can't be source or targets of relations
        catalog.unindex(ob)
        return

    uid = get_oid(ob, None)
    if uid is None:
        return

    rels = list(catalog.findRelations({'source_id': uid}))
    for rel in rels:
        registry.notify(RelationSourceDeletedEvent(ob, rel))
        parent = rel.__parent__
        try:
            del parent[rel.__name__]
        except KeyError:
            continue

    rels = list(catalog.findRelations({'target_id': uid}))
    for rel in rels:
        registry.notify(RelationTargetDeletedEvent(ob, rel))
        parent = rel.__parent__
        try:
            del parent[rel.__name__]
        except KeyError:
            continue
