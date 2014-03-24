# -*- coding: utf-8 -*-
from pyramid.events import subscriber
from pyramid.threadlocal import get_current_registry
from substanced.event import RootAdded
from substanced.event import subscribe_removed
from substanced.catalog import oid_from_resource

from dace.relations import get_relations_catalog
from .interfaces import (
    IRelationAdded,
    IRelationModified,
    IRelationDeleted,
    IRelationValue,
    )
from .catalog import create_catalog
from .events import RelationSourceDeleted, RelationTargetDeleted


@subscriber(RootAdded)
def add_relations_catalog(event):
    root = event.object
    create_catalog(root)


@subscriber(IRelationAdded)
def add_relation(event):
    relation = event.object
    catalog = get_relations_catalog()
    objectid = oid_from_resource(relation)
    catalog.index_doc(objectid, relation)


@subscriber(IRelationModified)
def update_relation(event):
    relation = event.object
    catalog = get_relations_catalog()
    objectid = oid_from_resource(relation)
    catalog.reindex_doc(objectid, relation)


@subscriber(IRelationDeleted)
def delete_relation(event):
    relation = event.object
    catalog = get_relations_catalog()
    objectid = oid_from_resource(relation)
    catalog.unindex_doc(objectid)


# FIXME doesn't go in there
@subscribe_removed
def object_deleted(event):
    registry = get_current_registry()
    ob = event.object
    catalog = get_relations_catalog()
    if catalog is None:
        # We don't have a Catalog installed in this part of the site
        return

    # FIXME do we need this if we have the delete_relation subscriber?
    if IRelationValue.providedBy(ob):
        # We assume relations can't be source or targets of relations
        objectid = oid_from_resource(ob)
        catalog.unindex_doc(objectid)
        return

    objectid = oid_from_resource(ob)
    rels = catalog['source_id'].eq(objectid).execute().all()
    for rel in rels:
        registry.notify(RelationSourceDeleted(ob, rel))
        parent = rel.__parent__
        try:
            del parent[rel.__name__]
        except KeyError:
            continue

    rels = catalog['target_id'].eq(objectid).execute().all()
    for rel in rels:
        registry.notify(RelationTargetDeleted(ob, rel))
        parent = rel.__parent__
        try:
            del parent[rel.__name__]
        except KeyError:
            continue
