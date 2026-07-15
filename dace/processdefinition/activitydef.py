# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi

"""Activity and sub-process definitions.

``contexts`` is the list of behaviour classes (business actions) bound
to the activity; registering them sets their ``node_definition``
back-reference — the reference rebuilt at application startup, hence
the mandatory restart after ``process_definitions_evolve``.
"""
from zope.interface import implementer
from persistent.list import PersistentList

from dace.interfaces import IActivityDefinition
from dace.processinstance.activity import Activity, SubProcess
from .eventdef import EventHandlerDefinition


@implementer(IActivityDefinition)
class ActivityDefinition(EventHandlerDefinition):
    """Definition of an activity carrying behaviour classes (``contexts``)."""
    factory = Activity

    def __init__(self, contexts=(), **kwargs):
        super(ActivityDefinition, self).__init__(**kwargs)
        self.contexts = PersistentList([])
        self._init_contexts(contexts)

    def _init_contexts(self, contexts):
        """Attach the behaviour classes and set their ``node_definition`` back-reference."""
        self.contexts = PersistentList(contexts)
        for context in contexts:
            context.node_definition = self

    def init_process_contexts(self, process):
        """Aggregate the behaviours' context interfaces on the process definition."""
        for context in self.contexts:
            if context.context not in process.contexts:
                process.contexts.append(context.context) 


class SubProcessDefinition(ActivityDefinition):
    """Activity spawning a sub-process (``sub_process_definition``)."""
    factory = SubProcess

    def __init__(self, contexts=(), pd=None, **kwargs):
        super(SubProcessDefinition, self).__init__(contexts, **kwargs)
        self.sub_process_definition = pd

    def _init_subprocess(self, process, subprocess):
        """Hook run when an instance spawns the sub-process (default: nothing)."""
        pass
