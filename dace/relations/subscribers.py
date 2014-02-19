# -*- coding: utf-8 -*-
from pyramid.events import subscriber
from pyramid.threadlocal import get_current_registry
from substanced.event import RootAdded
from substanced.interfaces import IObjectWillBeRemoved
from substanced.util import get_oid

from .interfaces import (
    ICatalog,
    IRelationAdded,
    IRelationModified,
    IRelationValue,
    )
from .catalog import create_catalog
from .events import RelationSourceDeleted, RelationTargetDeleted


@subscriber(RootAdded)
def add_relations_catalog(event):
    root = event.object
    create_catalog(root)


@subscriber(IRelationValue, IRelationModified)
def update_relation(relation, event):
    registry = get_current_registry()
    catalog = registry.getUtility(ICatalog)
    catalog.unindex(relation)
    catalog.index_doc(get_oid(relation), relation)


@subscriber(IRelationValue, IRelationAdded)
def add_relation(relation, event):
    registry = get_current_registry()
    catalog = registry.getUtility(ICatalog)
    objectid = get_oid(relation)
    catalog.index_doc(objectid, relation)


@subscriber(IObjectWillBeRemoved)
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
        registry.notify(RelationSourceDeleted(ob, rel))
        parent = rel.__parent__
        try:
            del parent[rel.__name__]
        except KeyError:
            continue

    rels = list(catalog.findRelations({'target_id': uid}))
    for rel in rels:
        registry.notify(RelationTargetDeleted(ob, rel))
        parent = rel.__parent__
        try:
            del parent[rel.__name__]
        except KeyError:
            continue
