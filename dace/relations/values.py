# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Vincent Fretin, Amen Souissi

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
    return [i.__identifier__ for i in Declaration(*interfaces).flattened()]

@colander.deferred
def missing_target(node, kw):
    context = node.bindings['context']
    return context.target_id

@colander.deferred
def missing_source(node, kw):
    context = node.bindings['context']
    return context.source_id

class RelationValueSchema(Schema):

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
