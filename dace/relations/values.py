# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Vincent Fretin, Amen Souissi

"""The relation object and its SDI editing schema.

``RelationValue`` resolves its ends lazily through the objectmap and
exposes the flattened interfaces of both ends — the keyword indexes
used to query relations by interface.
"""
import deform
import colander
from persistent import Persistent
from substanced.util import find_objectmap
from substanced.schema import Schema
from substanced.content import content
from substanced.property import PropertySheet

from zope.interface import implementer, providedBy, Declaration

from .interfaces import IRelationValue


def _interfaces_flattened(interfaces):
    """Identifiers of the interfaces, base interfaces included."""
    return [i.__identifier__ for i in Declaration(*interfaces).flattened()]

@colander.deferred
def missing_target(node, kw):
    """Colander deferred: default target from the edited relation."""
    context = node.bindings['context']
    return context.target_id

@colander.deferred
def missing_source(node, kw):
    """Colander deferred: default source from the edited relation."""
    context = node.bindings['context']
    return context.source_id

class RelationValueSchema(Schema):

    """SDI editing schema of a relation (name, type, ends, tags)."""
    relation_id = colander.SchemaNode(
                colander.String(),
                widget = deform.widget.TextInputWidget(),
                title='name'
                )

    reftype = colander.SchemaNode(
                colander.String(),
                widget = deform.widget.TextInputWidget(),
                title='Type'
                )

    source_id = colander.SchemaNode(
                colander.String(),
                widget = deform.widget.TextInputWidget(readonly=True),
                title='Source',
                missing=missing_source
                )

    target_id = colander.SchemaNode(
                colander.String(),
                widget = deform.widget.TextInputWidget(readonly=True),
                title='Target',
                missing=missing_target
                )

    tags = colander.SchemaNode(
                colander.Sequence(),
                colander.SchemaNode(
                    colander.String(),
                    name="tag",
                    widget=deform.widget.TextInputWidget()
                    ),
                widget=deform.widget.SequenceWidget(),
                title='Tags'
                )


class RelationValuePropertySheet(PropertySheet):
    """SDI property sheet exposing the schema."""
    schema = RelationValueSchema()


@content(
    'relationvalue',
    icon='glyphicon glyphicon-align-left',
    propertysheets=(
        ('Basic', RelationValuePropertySheet),
        ),
    )
@implementer(IRelationValue)
class RelationValue(Persistent):

    """A stored relation: source/target oids, ``relation_id``, ``reftype``, ``tags``."""
    def __init__(self, source_id, target_id, relation_id=None,
            reftype=None, tags=None):
        self.source_id = source_id
        self.target_id = target_id
        self.relation_id = relation_id or ''
        self.reftype = reftype or ''
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
        """The source object (resolved via the objectmap, cached resolver)."""
        return self.__resolve(self.source_id)

    @property
    def target(self):
        """The target object (resolved via the objectmap, cached resolver)."""
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
        """Interfaces provided by the source."""
        return providedBy(self.source)

    @property
    def from_interfaces_flattened(self):
        """Source interfaces, flattened (indexed)."""
        return _interfaces_flattened(self.from_interfaces)

    @property
    def to_interfaces(self):
        """Interfaces provided by the target."""
        return providedBy(self.target)

    @property
    def to_interfaces_flattened(self):
        """Target interfaces, flattened (indexed)."""
        return _interfaces_flattened(self.to_interfaces)
