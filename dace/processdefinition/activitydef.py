from zope.interface import implementer

from dace.interfaces import IActivityDefinition
from dace.processinstance.activity import Activity, SubProcess
from .eventdef import EventHandlerDefinition


@implementer(IActivityDefinition)
class ActivityDefinition(EventHandlerDefinition):
    factory = Activity

    def __init__(self, contexts=(), **kwargs):
        super(ActivityDefinition, self).__init__(**kwargs)
        self._init_contexts(contexts)

    def _init_contexts(self, contexts):
        self.contexts = contexts
        for context in contexts:
            context.node_definition = self


class SubProcessDefinition(ActivityDefinition):
    factory = SubProcess

    def __init__(self, contexts=(), pd=None, **kwargs):
        super(SubProcessDefinition, self).__init__(contexts, **kwargs)
        self.sub_process_definition = pd

    def _init_subprocess(self, process, subprocess):
        pass
