# Copyright (c) 2014 by Ecreall under licence AGPL terms
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Vincent Fretin, Amen Souissi

"""Monkey-patches applied by DaCE at import time.

Exactly three patches, all performance/latency motivated (see
docs/en/architecture.md, section 8):

1. ``tornado.ioloop._POLL_TIMEOUT`` lowered to 0.2 s so that timer and
   conditional events fire with sub-second reactivity.
2. ``substanced.objectmap.ObjectMap._find_resource`` replaced by a direct
   BTree walk: the original went through ``pyramid.traversal`` and created
   a Request object per lookup, which dominated profiles on large sites.
3. ``substanced.locking._get_lock_service`` short-circuited through
   dace's ``find_service`` for the same reason.

These patches assume substanced 1.0a1 internals and must be re-evaluated
when the maintained substanced fork lands (Phase 3 of the roadmap).
"""
import tornado.ioloop
tornado.ioloop._POLL_TIMEOUT = 0.2

from dace.util import find_service

# The original ObjectMap._find_resource used pyramid.traversal.find_resource which uses pyramid.traversal.traverse which create a Request object...
# We use a simpler implementation for performance.
from substanced.objectmap import ObjectMap

def _find_resource(self, context, path_tuple):
    if context is None:
        context = self.root

    obj = context
    # first segment is empty string
    for segment in path_tuple[1:]:
        # bypass substanced folder __getitem_ and get it directly from the BTree
        obj = obj.data[segment]

    return obj

ObjectMap._find_resource = _find_resource

# patch _get_lock_service to use our simplified find_service for performance
def _get_lock_service(resource):
    locks = find_service('locks')
    if locks is None:
        raise ValueError('No lock service in lineage')
    return locks

import substanced.locking
substanced.locking._get_lock_service = _get_lock_service
