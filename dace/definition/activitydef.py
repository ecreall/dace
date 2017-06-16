# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi

from zope.interface import implementer
from persistent.list import PersistentList

from dace.interfaces import IActivityDefinition
from dace.instance.activity import Activity, SubProcess
from .eventdef import EventHandlerDefinition


@implementer(IActivityDefinition)
class ActivityDefinition(EventHandlerDefinition):
    factory = Activity

    def __init__(self, behaviors=(), **kwargs):
        super(ActivityDefinition, self).__init__(**kwargs)
        self.behaviors = PersistentList([])
        self._init_behaviors(behaviors)

    def _init_behaviors(self, behaviors):
        self.behaviors = PersistentList(behaviors)
        for behavior in behaviors:
            behavior.node_definition = self

    def init_process_contexts(self, process):
        for behavior in self.behaviors:
            if behavior.context not in process.contexts:
                process.contexts.append(behavior.context)


class SubProcessDefinition(ActivityDefinition):
    factory = SubProcess

    def __init__(self, behaviors=(), pd=None, **kwargs):
        super(SubProcessDefinition, self).__init__(behaviors, **kwargs)
        self.sub_process_definition = pd

    def _init_subprocess(self, process, subprocess):
        pass
