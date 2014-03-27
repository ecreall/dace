from persistent import Persistent
from substanced.util import find_objectmap
from zope.interface import implementer, providedBy, Declaration

from .interfaces import IRelationValue


def _interfaces_flattened(interfaces):
    return [i.__identifier__ for i in Declaration(*interfaces).flattened()]


@implementer(IRelationValue)
class RelationValue(Persistent):

    def __init__(self, source_id, target_id, relation_id, tags=None):
        self.source_id = source_id
        self.target_id = target_id
        self.relation_id = relation_id
        if tags is None:
            tags = []
        self.tags = tags

    def __resolve(self, content_id):
        try:
            resolver = self._v_resolver
        except AttributeError:
            objectmap = find_objectmap(self)
            resolver = self._v_resolver = objectmap.object_for
        try:
            return resolver(content_id)
        except KeyError:
            return None

    @property
    def source(self):
        return self.__resolve(self.source_id)

    @property
    def target(self):
        return self.__resolve(self.target_id)

    def __repr__(self):
        return u"""RelationValue(
    source=%s,
    target=%s,
    tags=%s)""" % (
                u"%s <%s>" % (self.source.__name__, self.source.__class__.__name__),
                u"%s <%s>" % (self.target.__name__, self.target.__class__.__name__),
                self.tags or "None")

    @property
    def from_interfaces(self):
        return providedBy(self.source)

    @property
    def from_interfaces_flattened(self):
        return _interfaces_flattened(self.from_interfaces)

    @property
    def to_interfaces(self):
        return providedBy(self.target)

    @property
    def to_interfaces_flattened(self):
        return _interfaces_flattened(self.to_interfaces)
