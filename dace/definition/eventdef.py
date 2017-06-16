# Copyright (c) 2014 by Ecreall under licence AGPL terms
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi

from .core import FlowNodeDefinition, Path
from dace.instance.event import (
    StartEvent, TerminateEvent, EndEvent,
    TimerEvent, SignalEvent, IntermediateCatchEvent,
    IntermediateThrowEvent, ConditionalEvent)
from dace.instance.workitem import StartWorkItem

from dace.instance.core import EventHandler


class EventHandlerDefinition(FlowNodeDefinition):
    factory = EventHandler
    boundaryEvents = ()

    def __init__(self, **kwargs):
        super(EventHandlerDefinition, self).__init__(**kwargs)


class EventDefinition(FlowNodeDefinition):

    def __init__(self, event_kind=None, **kwargs):
        super(EventDefinition, self).__init__(**kwargs)
        self.event_kind = event_kind
        self.behaviors = ()

    def create(self):
        event_kind = self.event_kind and self.event_kind.create() or None
        return self.factory(self, event_kind)


class StartEventDefinition(EventDefinition):
    factory = StartEvent

    def start_process(self, transaction):
        start_workitems = {}
        if self.event_kind is None:
            for transition in self.outgoing:
                if transition.condition(None):
                    nodedef = self.process[transition.target_id]
                    initial_path = Path([transition], transaction)
                    startable_paths = nodedef.find_startable_paths(initial_path,
                                                                   self)
                    for startable_path in startable_paths:
                        swi = StartWorkItem(startable_path, self)
                        node_name = swi.node.__name__
                        if node_name in start_workitems:
                            start_workitems[node_name].merge(swi)
                        else:
                            start_workitems[node_name] = swi

        return start_workitems


class IntermediateThrowEventDefinition(EventDefinition):
    factory = IntermediateThrowEvent


class IntermediateCatchEventDefinition(EventDefinition):
    factory = IntermediateCatchEvent


class EndEventDefinition(EventDefinition):
    factory = EndEvent


class EventKindDefinition(object):
    factory = NotImplemented

    def create(self):
        return self.factory()


class SignalEventDefinition(EventKindDefinition):

    factory = SignalEvent

    def __init__(self, ref_signal=None, **kwargs):
        super(SignalEventDefinition, self).__init__(**kwargs)
        self.ref_signal = ref_signal


class TerminateEventDefinition(EventKindDefinition):

    factory = TerminateEvent


class ConditionalEventDefinition(EventKindDefinition):

    factory = ConditionalEvent

    # the condition is a function with the process as parameter
    def __init__(self, condition, **kwargs):
        super(ConditionalEventDefinition, self).__init__(**kwargs)
        self.condition = condition
        self.initialize()

    def initialize(self):
        return


class TimerEventDefinition(EventKindDefinition):
    factory = TimerEvent

    def __init__(self, time_date=None,
                 time_duration=None,
                 time_cycle=None,
                 **kwargs):
        super(TimerEventDefinition, self).__init__(**kwargs)
        self.time_date = time_date
        self.time_duration = time_duration
        self.time_cycle = time_cycle
