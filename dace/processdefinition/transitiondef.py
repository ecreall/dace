# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi

"""Transition definitions.

Named ``'<source_id>-<target_id>'``; ``condition`` guards the
transition (``sync=True`` defers the evaluation to consumption time);
``set_source``/``set_target`` support the rewiring done by the
normalisation.
"""
from zope.interface import implementer

from dace.interfaces import ITransitionDefinition
from dace.descriptors import SharedUniqueProperty
from dace.objectofcollaboration.object import Object
from dace.processinstance.transition import Transition


def always_true(data):
    """Default transition condition."""
    return True


@implementer(ITransitionDefinition)
class TransitionDefinition(Object):

    """Edge of the definition graph (source/target resolved by name)."""
    factory = Transition
    target = SharedUniqueProperty('target', 'incoming', False)
    source = SharedUniqueProperty('source', 'outgoing', False)
    process = SharedUniqueProperty('process', 'transitions', False)

    def __init__(self, 
                 source_id, 
                 target_id, 
                 condition=always_true, 
                 sync=False, 
                 **kwargs):
        super(TransitionDefinition, self).__init__(**kwargs)
        self.id = '%s-%s' % (source_id, target_id)
        self.source_id = source_id
        self.target_id = target_id
        self.condition = condition
        self.sync = sync

    def _init_ends(self, process=None):
        """Resolve and wire source and target in the (given or own) process."""
        if process is None:
            process = self.process

        if process is not None:
            self.setproperty('source', process[self.source_id])
            self.setproperty('target', process[self.target_id])

    def create(self):
        """Instantiate the runtime transition."""
        return self.factory(self)

    def set_target(self, newtarget):
        """Re-point the target (updates id) — used by the normalisation."""
        self.target_id = newtarget.__name__
        self.id = '%s-%s' % (self.source_id, self.target_id)
        self.setproperty('target', newtarget)

    def set_source(self, newsource):
        """Re-point the source (updates id) — used by the normalisation."""
        self.source_id = newsource.__name__
        self.id = '%s-%s' % (self.source_id, self.target_id)
        self.setproperty('source', newsource)

    def equal(self, other):
        """Equality by transition id."""
        return self.id == other.id

    def __repr__(self):# pragma: no cover
        return "%s(%r, %r)" % (self.__class__.__name__,
                self.source, self.target)
