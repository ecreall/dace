# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi

from dace.descriptors import SharedUniqueProperty
from dace.model.object import Object

class Transition(Object):

    target = SharedUniqueProperty('target', 'incoming', False)
    source = SharedUniqueProperty('source', 'outgoing', False)
    process = SharedUniqueProperty('process', 'transitions', False)

    def __init__(self, definition):
        super(Transition, self).__init__()
        self.id = definition.id

    def _init_ends(self, process, definition):
        self.setproperty('source', process[definition.source.__name__])
        self.setproperty('target', process[definition.target.__name__])

    @property
    def definition(self):
        return self.process.definition[self.id]

    @property
    def condition(self):
        return self.definition.condition

    @property
    def sync(self):
        return self.definition.sync

    def validate(self, process):
        if not self.sync and hasattr(self, 'condition_result'):
            return self.condition_result

        self.condition_result = self.condition(process)
        return self.condition_result

    def equal(self, transition):
        return self.id == transition.id

    def __repr__(self):# pragma: no cover
        return "Transition(%r, %r)" % (self.source, self.target)
