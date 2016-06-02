# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi

from zope.interface import implementer
from persistent.list import PersistentList

from dace.interfaces import IActivityDefinition
from dace.processinstance.activity import Activity, SubProcess
from .eventdef import EventHandlerDefinition


@implementer(IActivityDefinition)
class ActivityDefinition(EventHandlerDefinition):
    factory = Activity

    def __init__(self, contexts=(), **kwargs):
        super(ActivityDefinition, self).__init__(**kwargs)
        self.contexts = PersistentList([])
        self._init_contexts(contexts)

    def _init_contexts(self, contexts):
        self.contexts = PersistentList(contexts)
        for context in contexts:
            context.node_definition = self

    def init_process_contexts(self, process):
        for context in self.contexts:
            if context.context not in process.contexts:
                process.contexts.append(context.context) 


class SubProcessDefinition(ActivityDefinition):
    factory = SubProcess

    def __init__(self, contexts=(), pd=None, **kwargs):
        super(SubProcessDefinition, self).__init__(contexts, **kwargs)
        self.sub_process_definition = pd

    def _init_subprocess(self, process, subprocess):
        pass
