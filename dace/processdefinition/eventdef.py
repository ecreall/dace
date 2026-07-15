# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi

"""Event definitions and their kinds.

``EventDefinition.create`` instantiates the runtime event together with
its kind; ``StartEventDefinition.start_process`` is where the virtual
``StartWorkItem``s are built by exploring startable paths. Kind
definitions carry the parameters: ``refSignal`` (signal),
``condition`` (conditional), ``time_date``/``time_duration``/
``time_cycle`` callables (timer).
"""
from .core import FlowNodeDefinition, Path
from dace.processinstance.event import (StartEvent, TerminateEvent, EndEvent,
    TimerEvent, SignalEvent, IntermediateCatchEvent,
    IntermediateThrowEvent, ConditionalEvent)
from dace.processinstance.workitem import StartWorkItem

from dace.processinstance.core import EventHandler

class EventHandlerDefinition(FlowNodeDefinition):
    """Definition of a node that may carry boundary events (see runtime FIXME)."""
    factory = EventHandler
    boundaryEvents = ()

    def __init__(self, **kwargs):
        super(EventHandlerDefinition, self).__init__(**kwargs)

class EventDefinition(FlowNodeDefinition):

    """Definition of an event node, optionally parameterised by an ``EventKindDefinition``."""
    def __init__(self, eventKind=None, **kwargs):
        super(EventDefinition, self).__init__( **kwargs)
        self.eventKind = eventKind
        self.contexts = ()

    def create(self):
        """Instantiate the runtime event with a fresh instance of its kind."""
        event_kind = self.eventKind and self.eventKind.create() or None
        return self.factory(self, event_kind)


class StartEventDefinition(EventDefinition):
    """Start event: entry point of the definition graph."""
    factory = StartEvent

    def start_process(self, transaction):
        """Build the virtual start work-items: explore each valid outgoing
        transition, turn every startable path into a ``StartWorkItem`` and
        merge those reaching the same node. Only empty-kind start events
        offer them.
        """
        start_workitems = {}
        if self.eventKind is None:
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
    """Intermediate emitting event."""
    factory = IntermediateThrowEvent


class IntermediateCatchEventDefinition(EventDefinition):
    """Intermediate waiting event (timer/signal/condition)."""
    factory = IntermediateCatchEvent


class EndEventDefinition(EventDefinition):
    """End event: closes the process (or the path, with a Terminate kind)."""
    factory = EndEvent


class EventKindDefinition(object):
    """Base of the kind definitions; ``create`` instantiates the runtime kind."""
    factory = NotImplemented

    def create(self):
        """Instantiate the runtime kind (``factory()``)."""
        return self.factory()


class SignalEventDefinition(EventKindDefinition):

    """``refSignal(process)`` names the signal thrown/caught."""
    factory = SignalEvent

    def __init__(self, refSignal=None, **kwargs):
        super(SignalEventDefinition, self).__init__( **kwargs)
        self.refSignal = refSignal


class TerminateEventDefinition(EventKindDefinition):

    """Marker kind: end the path without the process cleanup."""
    factory = TerminateEvent


class ConditionalEventDefinition(EventKindDefinition):

    """``condition(process)`` is polled by the runtime kind (1 s)."""
    factory = ConditionalEvent

    # the condition is a function with the process as parameter
    def __init__(self, condition, **kwargs):
        super(ConditionalEventDefinition, self).__init__(**kwargs)
        self.condition = condition
        self.initialize()

    def initialize(self):
        """Subclass hook run at construction."""
        return


class TimerEventDefinition(EventKindDefinition):
    """Timer parameters, each a callable of the process: ``time_date``
    (datetime), ``time_duration`` (timedelta) or ``time_cycle``
    (not implemented by the runtime).
    """
    factory = TimerEvent

    def __init__(self, time_date=None,
                 time_duration=None,
                 time_cycle=None,
                 **kwargs):
        super(TimerEventDefinition, self).__init__(**kwargs)
        self.time_date = time_date
        self.time_duration = time_duration
        self.time_cycle = time_cycle
