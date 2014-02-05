from .event import ConditionalEvent
from .core import FlowNodeDefinition
from .event import (StartEvent, TerminateEvent, EndEvent,
    TimerEvent, SignalEvent, IntermediateCatchEvent, IntermediateThrowEvent)


class EventDefinition(FlowNodeDefinition):

    def __init__(self, eventKind=None):
        super(EventDefinition, self).__init__()
        self.eventKind = eventKind
        self.contexts = ()

    def create(self, process):
        eventKind = self.eventKind and self.eventKind.create() or None
        return self.factory(process, self, eventKind)


class StartEventDefinition(EventDefinition):
    factory = StartEvent


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
    # la condition doit avoir le processus comme parametre
    def __init__(self, condition=None):
        super(ConditionalEventDefinition, self).__init__()
        if condition is None:
            self.condition = lambda self: True
        else:
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
