from dace.descriptors import SharedUniqueProperty
from dace.objectofcollaboration.object import Object

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

    def equal(self, transition):
        return self.source is transition.source and self.target is transition.target

    def __repr__(self):# pragma: no cover
        return "Transition(%r, %r)" % (self.source, self.target)
