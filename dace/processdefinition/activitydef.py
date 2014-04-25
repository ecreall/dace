from zope.interface import implements

from dace.interfaces import IActivityDefinition
from dace.processinstance.activity import Activity, SubProcess
from .eventdef import EventHandlerDefinition


class ActivityDefinition(EventHandlerDefinition):
    factory = Activity
    implements(IActivityDefinition)

    def __init__(self, contexts=(), **kwargs):
        super(ActivityDefinition, self).__init__(**kwargs)
        self._init_contexts(contexts)

    def _init_contexts(self, contexts):
        self.contexts = contexts
        for c in contexts:
            c.node_definition = self


class SubProcessDefinition(ActivityDefinition):
    factory = SubProcess

    def __init__(self, contexts=(), pd=None, **kwargs):
        super(SubProcessDefinition, self).__init__(contexts, **kwargs)
        self.sub_process_definition = pd
