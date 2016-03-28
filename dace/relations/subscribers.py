# -*- coding: utf-8 -*-
# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Vincent Fretin, Amen Souissi

from pyramid.events import subscriber
from pyramid.threadlocal import get_current_registry
from pyramid.threadlocal import get_current_request
from substanced.catalog import oid_from_resource
from substanced.event import RootAdded
from substanced.event import subscribe_removed
from substanced.util import find_objectmap

from dace.relations import get_relations_catalog, invalidate_cache
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
    catalog = get_relations_catalog(relation.source)
    objectid = oid_from_resource(relation)
    catalog.index_doc(objectid, relation)


@subscriber(IRelationModified)
def update_relation(event):
    relation = event.object
    catalog = get_relations_catalog(relation.source)
    objectid = oid_from_resource(relation)
    catalog.reindex_doc(objectid, relation)


@subscriber(IRelationDeleted)
@subscribe_removed()
def object_deleted(event):
    if getattr(event, 'moving', False):
        return

    registry = get_current_registry()
    request = get_current_request()
    if not request:
        return

    objectmap = find_objectmap(request.root)
    ob = event.object
    catalog = get_relations_catalog(request.root)
    if catalog is None:
        # We don't have a Catalog installed in this part of the site
        return

    if IRelationValue.providedBy(ob):
        # We assume relations can't be source or targets of relations
        objectid = oid_from_resource(ob)
        catalog.unindex_doc(objectid)
        return

    objectid = oid_from_resource(ob)
    rels = catalog['source_id'].eq(objectid).execute(
                   resolver=objectmap.object_for).all()
    for rel in rels:
        registry.notify(RelationSourceDeleted(ob, rel))
        parent = rel.__parent__
        try:
            parent.remove(rel.__name__, send_events=False, registry=registry)
        except KeyError:
            continue

    rels = catalog['target_id'].eq(objectid).execute(
                  resolver=objectmap.object_for).all()
    for rel in rels:
        registry.notify(RelationTargetDeleted(ob, rel))
        parent = rel.__parent__
        try:
            parent.remove(rel.__name__, send_events=False, registry=registry)
        except KeyError:
            continue

    invalidate_cache()
