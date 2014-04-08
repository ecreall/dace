from dace.objectofcollaboration.object import Object, SHARED_UNIQUE

class Transition(Object):

    properties_def = {'target': (SHARED_UNIQUE, 'incoming', False),
                      'source': (SHARED_UNIQUE, 'outgoing', False),
                      'process': (SHARED_UNIQUE, 'transitions', False)
                      }

    def __init__(self, process, definition):
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

    @property
    def process(self):
        return self.getproperty('process')
    
    @property
    def target(self):
        return self.getproperty('target')

    @property
    def source(self):
        return self.getproperty('source')


    def equal(self, transition):
        return self.source is transition.source and self.target is transition.target


    def __repr__(self):
        return "Transition(%r, %r)" % (self.source, self.target)
