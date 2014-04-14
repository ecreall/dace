from .core import FlowNodeDefinition, Path
from dace.processinstance.event import (StartEvent, TerminateEvent, EndEvent,
    TimerEvent, SignalEvent, IntermediateCatchEvent, IntermediateThrowEvent, ConditionalEvent)
from dace.processinstance.workitem import StartWorkItem

from dace.processinstance.core import EventHandler

class EventHandlerDefinition(FlowNodeDefinition):
    factory = EventHandler
    boundaryEvents = ()

    def __init__(self):
        super(FlowNodeDefinition, self).__init__()

class EventDefinition(FlowNodeDefinition):

    def __init__(self, eventKind=None):
        super(EventDefinition, self).__init__()
        self.eventKind = eventKind
        self.contexts = ()

    def create(self):
        eventKind = self.eventKind and self.eventKind.create() or None
        return self.factory(self, eventKind)


class StartEventDefinition(EventDefinition):
    factory = StartEvent

    def start_process(self, transaction):
        if self.eventKind is None:
            start_workitems = {}
            for transition in self.outgoing:
                if transition.condition(None):
                    nodedef = self.process[transition.target.__name__]
                    initial_path = Path([transition], transaction)
                    startable_paths = nodedef.find_startable_paths(initial_path, self)
                    for startable_path in startable_paths:
                        swi = StartWorkItem(startable_path)
                        if swi.node.__name__ in start_workitems:
                            start_workitems[swi.node.__name__].merge(swi)
                        else:
                            start_workitems[swi.node.__name__] = swi

            for swi in start_workitems.values():
                yield swi


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
    # Les parametres de l' __init__ sont calculables (i.e. des operations). Il faut donc les generer
    # voir avec les adaptateurs ....
    def __init__(self, refSignal=None):
        super(SignalEventDefinition, self).__init__()
        self.refSignal = refSignal


class TerminateEventDefinition(EventKindDefinition):
    factory = TerminateEvent


class ConditionalEventDefinition(EventKindDefinition):
    factory = ConditionalEvent
    # the condition is a function with the process as parameter
    def __init__(self, condition):
        super(ConditionalEventDefinition, self).__init__()
        self.condition = condition
        self.initialize()

    def initialize(self):
        return


class TimerEventDefinition(EventKindDefinition):
    factory = TimerEvent

    def __init__(self, time_date=None,
                 time_duration=None,
                 time_cycle=None):
        super(TimerEventDefinition, self).__init__()
        self.time_date = time_date
        self.time_duration = time_duration
        self.time_cycle = time_cycle
