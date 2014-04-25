from zope.interface import implements

from dace.interfaces import ITransitionDefinition
from dace.objectofcollaboration.object import Object, SHARED_UNIQUE
from dace.processinstance.transition import Transition

def always_true(data):
    return True


class TransitionDefinition(Object):

    factory = Transition
    implements(ITransitionDefinition)
    properties_def = {'target': (SHARED_UNIQUE, 'incoming', False),
                      'source': (SHARED_UNIQUE, 'outgoing', False),
                      'process': (SHARED_UNIQUE, 'transitions', False)
                      }

    def __init__(self, source_id, target_id, condition=always_true, sync=False, **kwargs):
        super(TransitionDefinition, self).__init__(**kwargs)
        self.id = '%s-%s' % (source_id, target_id)
        self.source_id = source_id
        self.target_id = target_id
        self.condition = condition
        self.sync = sync

    def _init_ends(self, process=None):
        if process is None:
            process = self.process
 
        if process is not None:
            self.setproperty('source', process[self.source_id])
            self.setproperty('target', process[self.target_id])

    def create(self):
        return self.factory(self)

    @property
    def target(self):
        return self.getproperty('target')

    @property
    def source(self):
        return self.getproperty('source')

    @property
    def process(self):
        return self.getproperty('process')

    def set_target(self, newtarget):
        self.target_id = newtarget.__name__
        self.id = '%s-%s' % (self.source_id, self.target_id)
        self.setproperty('target', newtarget)

    def set_source(self, newsource):
        self.source_id = newsource.__name__
        self.id = '%s-%s' % (self.source_id, self.target_id)
        self.setproperty('source', newsource)

    def equal(self, other): #deprecated
        return self.source is other.source and self.target is other.target

   # def __eq__(self, other):
   #     return self.source is other.source and self.target is other.target

    def __repr__(self):# pragma: no cover
        return "%s(%r, %r)" % (self.__class__.__name__,
                self.source, self.target)
