from zope.interface import implements

from dace.interfaces import IActivityDefinition
from dace.processinstance.activity import Activity, SubProcess
from .core import EventHandlerDefinition


class ActivityDefinition(EventHandlerDefinition):
    factory = Activity
    implements(IActivityDefinition)

    def __init__(self, contexts=()):
        super(ActivityDefinition, self).__init__()
        self.contexts = contexts


class SubProcessDefinition(ActivityDefinition):
    factory = SubProcess

    def __init__(self, contexts=(), pd=None):
        super(SubProcessDefinition, self).__init__(contexts)
        self.processDefinition = pd
