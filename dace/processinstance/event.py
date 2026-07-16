# Copyright (c) 2014 by Ecreall under licence AGPL terms
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi

"""Runtime events and their kinds.

``Event`` nodes (throwing/catching, start/intermediate/end) drive the
process through the reactor: catching kinds arm themselves through
``push_event_callback_after_commit`` (an after-commit hook scheduling an
``EventJob`` on the reactor loop), so an event only exists once the data that
created it is durably committed. ``TimerEvent`` waits for a
date/duration, ``ConditionalEvent`` re-polls its predicate every second,
``SignalEvent`` broadcasts/listens over a local zmq PUB/SUB socket, and
``TerminateEvent`` makes an ``EndEvent`` skip the process cleanup.
"""
import time
import transaction
import datetime

from pyramid.threadlocal import get_current_registry

import asyncio
import zmq

from .core import FlowNode, BehavioralFlowNode, ProcessFinished
from dace.util import (
    get_system_request,
    get_socket,
    DelayedCallback,
    get_zmq_context,
    get_async_zmq_context,
    EventJob,
    is_broken)
from dace import log


callbacks = {}


def push_event_callback_after_commit(event, callback, callback_params, deadline):
    # Create job object now before the end of the interaction so we have
    # the logged in user.
    """Arm ``callback`` for ``event`` at ``deadline`` (ms), but only if the
    current ZODB transaction commits: the ``EventJob`` is created *now* (to
    capture the logged-in user), its callable is set in the after-commit
    hook (the event then has a ``_p_oid``), and a ``DelayedCallback``
    schedules it on the IOLoop.
    """
    job = EventJob('system')
    def after_commit_hook(status, *args, **kws):
        # status is true if the commit succeeded, or false if the commit aborted.
        if status:
            # Set callable now, we are sure to have p_oid
            event, callback, callback_params, deadline, job = args
            job.callable = callback
            job.args = callback_params
            dc = DelayedCallback(job, deadline, event._p_oid)
            dc.start()

    transaction.get().addAfterCommitHook(after_commit_hook,
            args=(event, callback, callback_params, deadline, job))


class Event(BehavioralFlowNode, FlowNode):

    """A runtime event node.

    ``execution_prepared``/``execution_finished`` guard double execution;
    ``start`` executes the kind then finishes the behaviour;
    ``replay_path`` executes it when reached through a user decision.
    """
    def __init__(self, definition, eventKind, **kwargs):
        super(Event, self).__init__(definition, **kwargs)
        self.eventKind = eventKind
        self.execution_prepared = False
        self.execution_finished = False
        if eventKind:
            eventKind.event = self

    def __call__(self, transition):
        pass

    def prepare_for_execution(self):
        """Mark the event armed (kinds refine this by scheduling themselves)."""
        self.execution_prepared = True
        self.execution_finished = False

    def start(self, transaction):
        """If a work-item is available: execute the kind and finish the behaviour."""
        wi = self._get_workitem()
        if wi is not None:
            super(Event, self).start(transaction)
            self.execute()
            self.finish_behavior(wi)
            self.execution_finished = True
            self.execution_prepared = False
        else:
            self.stop()

    def replay_path(self, decision, transaction):
        """Execute on replay if not already done, then continue the replay."""
        if not self.execution_finished:
            self.execute()
            self.finish_behavior(decision)
            self.execution_finished = True
            self.execution_prepared = False

        super(Event, self).replay_path(decision, transaction)

    def validate(self):
        pass # pragma: no cover

    def execute(self):
        pass # pragma: no cover

    def stop(self):
        """Disarm the event."""
        self.execution_prepared = False


class Throwing(Event):

    """Event that *emits*: validated then started as soon as it is prepared."""
    def validate(self):
        return True

    def prepare_for_execution(self):
        """Fire immediately when valid (throwing events do not wait)."""
        if not self.execution_prepared:
            super(Throwing, self).prepare_for_execution()
            if self.validate():
                self.start(None)
            else:
                self.stop()

    def execute(self):
        """Delegate to the kind's ``execute`` (signal broadcast, ...)."""
        if self.eventKind is None:
            return

        return self.eventKind.execute()


class Catching(Event):

    """Event that *waits*: arming is delegated to the kind (timer, signal, ...)."""
    def validate(self):
        """Delegate to the kind's ``validate`` (empty kind: always valid)."""
        if self.eventKind is None:
            return True

        return self.eventKind.validate()

    def prepare_for_execution(self):
        # If it's a empty StartEvent, execute the callback directly.
        """Empty kind: fire now; otherwise let the kind schedule itself."""
        if not self.execution_prepared:
            super(Catching, self).prepare_for_execution()
            if self.eventKind is None:
                if self.validate():
                    self.start(None)
                else:
                    self.stop()
            else:
                self.eventKind.prepare_for_execution()

    def stop(self):
        """Disarm the event and its kind."""
        super(Catching, self).stop()
        if self.eventKind is not None:
            self.eventKind.stop()


class StartEvent(Catching):

    """Catching event that starts the process (guarded by ``process._started``)."""
    def start(self, transaction):
        """Start the process once, through the available work-item."""
        if not self.process._started:
            wi = self._get_workitem()
            if wi is not None:
                super(StartEvent, self).start(transaction)
                self.process.start()
                #self.finish_behavior(wi)
                self.execution_finished = True
            else:
                self.stop()
        else:
            self.stop()


class IntermediateThrowEvent(Throwing):
    """Throwing event in the middle of a flow."""
    pass # pragma: no cover


class IntermediateCatchEvent(Catching):
    """Catching event in the middle of a flow (timers, signals, conditions)."""
    pass # pragma: no cover


class EndEvent(Throwing):


    """Throwing event closing the process: stops every node, clears the
    work-items, notifies ``ProcessFinished``, unwinds a finished
    sub-process into its parent (``attachedTo``) and removes volatile
    processes from their holder — unless the kind is ``TerminateEvent``.
    """
    def finish_behavior(self, work_item):
        """Finish then run the process-closing policy described on the class."""
        super(EndEvent, self).finish_behavior(work_item)
        if isinstance(self.eventKind, TerminateEvent):
            return
        # Remove all workitems from process
        for node in self.process.nodes:
            try:
                node.stop()
                node.setproperty('workitems', [])
            except:
                pass

        self.process._finished = True
        registry = get_current_registry()
        registry.notify(ProcessFinished(self))
        current_process = self.process
        if current_process.definition.isSubProcess:
            try:
                request = get_system_request()
                root_process = current_process.attachedTo.process
                current_process.attachedTo.finish_execution(None, request)
                root_process.execution_context.remove_sub_execution_context(
                    current_process.execution_context)
                parent_node = current_process.attachedTo.node
                if current_process in parent_node.sub_processes:
                    parent_node.sub_processes.remove(current_process)
            except AttributeError as error:
                # the root process is a volatile subprocess (is removed)
                log.warning(error)

        if current_process.definition.isVolatile and \
           getattr(current_process, '__property__', None):
            getattr(current_process.__parent__.__class__,
                    current_process.__property__).remove(
                        current_process.__parent__, current_process)


class EventKind(object):

    # cette operation est appelee par les evenements "Catching"
    """Behaviour of an event: ``validate``/``prepare_for_execution`` (catching) and ``execute`` (throwing)."""
    def validate(self):
        """Catching side: may the event fire now?"""
        return True

    def prepare_for_execution(self, restart=False):
        """Catching side: schedule the wake-up (``restart=True`` on app restart)."""
        pass # pragma: no cover

    # cette operation est appelee par les evenements "Throwing"
    def execute(self):
        """Throwing side: emit."""
        pass # pragma: no cover

    def stop(self):
        """Disarm (cancel scheduled callbacks / close streams)."""
        pass # pragma: no cover

    @property
    def definition(self):
        """The matching ``EventKindDefinition``."""
        return self.event.definition.eventKind


class ConditionalEvent(EventKind):

    """Catching kind polling ``definition.condition(process)`` every second."""
    def validate(self):
        """Evaluate the condition against the process."""
        return self.definition.condition(self.event.process)

    def prepare_for_execution(self, restart=False):
        self._push_callback()

    def _callback(self):
        """Fire if the condition holds, else re-schedule in 1 s."""
        if self.event._p_oid in callbacks:
            del callbacks[self.event._p_oid]

        if self.validate():
            #log.info('%s %s', self.event, "validate ok")
            wi = self.event._get_workitem()
            if wi is not None:
                self.event.start(None)
            else:
                self.stop()
        else:
            #log.info('%s %s', self.event, "validate ko, retry in 1s")
            self._push_callback()

    def _push_callback(self):
        """Schedule the next poll (1 s) through the after-commit hook."""
        push_event_callback_after_commit(self.event, self._callback, (), 1000)

    def stop(self):
        """Cancel the scheduled callback through the reactor socket."""
        get_socket().send_pyobj(('stop', self.event._p_oid))


class TerminateEvent(EventKind):
    """Marker kind: the ``EndEvent`` ends the path without process cleanup."""
    pass


# https://github.com/zeromq/pyzmq/blob/master/examples/poll/pubsub.py
# http://learning-0mq-with-pyzmq.readthedocs.org/en/latest/pyzmq/multisocket/tornadoeventloop.html

def get_signal_socket_url():
    """Local PUB/SUB endpoint used by signal events."""
    return 'tcp://127.0.0.1:12346'


class Listener(object):
    """Loop-side zmq SUB subscription delivering a signal to its ``EventJob``.

    Picklable (sent over the command socket); the socket and the asyncio
    task are only created in ``start``, inside the reactor loop thread.
    """
    def __init__(self, job, identifier):
        self.job = job
        self.identifier = identifier
        self._sock = None
        self._task = None

    def start(self):
        """Subscribe to the signal socket; on message, close the stream and run
        the job 2 s later (leaving the throwing transaction time to commit).
        Runs in the event-loop thread: no ZODB access here, the job was built
        beforehand.
        """
        identifier = self.identifier
        job = self.job
        def execute_next(msg):
            # We can't use zodb object from outside here because
            # this code is executed in another thread (eventloop)
            # We don't have site or interaction, so the job must be created
            # before.
            # we can't use push_event_callback_after_commit here because
            # it will never commit in this thread (eventloop)
            if identifier in callbacks:
                callbacks[identifier].close()
                del callbacks[identifier]

            job.args = (msg, )
            # wait 2s that the throw event transaction has committed
            dc = DelayedCallback(job, 2000)
            dc.start()

        ctx = get_async_zmq_context()
        sock = ctx.socket(zmq.SUB)
        sock.setsockopt_string(zmq.SUBSCRIBE, u'')
        sock.connect(get_signal_socket_url())
        self._sock = sock

        async def listen():
            msg = await sock.recv_multipart()
            execute_next(msg)

        # register ourselves (the consumer registered the object it
        # unpickled — that is this Listener), then wait for one message
        callbacks[identifier] = self
        self._task = asyncio.get_event_loop().create_task(listen())

    def close(self):
        """Cancel the subscription (reactor loop thread)."""
        if self._task is not None:
            self._task.cancel()
            self._task = None
        if self._sock is not None:
            self._sock.close(0)
            self._sock = None


class SignalEvent(EventKind):

    """Kind thrown/caught by reference (``refSignal``) over zmq PUB/SUB."""
    _msg = None

    def validate(self):
        """True when the received message matches ``refSignal(process)``."""
        return self.definition.refSignal(self.event.process) == self._msg

    def prepare_for_execution(self, restart=False):
        """Commit (to get ``_p_oid``), then register a ``Listener`` via the reactor."""
        job = EventJob('system')
        transaction.commit()  # needed to have self.event._p_oid
        job.callable = self._callback
        event_oid = self.event._p_oid
        listener = Listener(job, event_oid)
        get_socket().send_pyobj(('start', listener))

    def stop(self):
        # close ZMQStream
        """Close the listening stream through the reactor socket."""
        get_socket().send_pyobj(('close', self.event._p_oid))

    def _callback(self, msg):
        # convert str (py27) / bytes (py34) to unicode (py27) or str (py34)
        """Decode the message and fire the event when it matches."""
        self._msg = msg[0].decode('utf-8')
        if self.validate():
            wi = self.event._get_workitem()
            if wi is not None:
                self.event.start(None)
            else:
                self.event.stop()

    def execute(self):
        """Broadcast ``refSignal(process)`` on the signal socket (throwing side)."""
        ref = self.definition.refSignal(self.event.process)
        ctx = get_zmq_context()
        s = ctx.socket(zmq.PUB)
        s.bind(get_signal_socket_url())
        # Sleep to allow sockets to connect.
        time.sleep(0.2)
        s.send_string(ref)
        s.close()


class TimerEvent(EventKind):

    """Catching kind waiting for ``time_date`` or ``time_duration`` (both
    computed by definition callables against the process; ``time_cycle`` is
    not implemented). On application restart the stored value is reused
    unless broken (``restart=True``).
    """
    def __init__(self):
        super(TimerEvent, self).__init__()
        self.time_date = None
        self.time_duration = None
        self.time_cycle = None

    def _prepare_time(self, time, restart=False):
        """Compute and store the time attribute (recompute unless restarting)."""
        time_attr = getattr(self, time, None)
        if is_broken(time_attr) or time_attr is None or not restart:
            setattr(self, time, getattr(self.definition, time)(self.event.process))#TODO

    def _start_time(self, restart=False):
        """Return start time in milliseconds.
        """
        if self.definition.time_date is not None:
            self._prepare_time('time_date', restart)
            if not isinstance(self.time_date, datetime.datetime):
                raise TypeError("Unsupported deadline %r" % self.time_date)
            return (time.mktime(self.time_date.timetuple()) - time.time()) * 1000
        elif self.definition.time_duration is not None:
            self._prepare_time('time_duration', restart)
            if not isinstance(self.time_duration, datetime.timedelta):
                raise TypeError("Unsupported deadline %r" % self.time_duration)
            return self.time_duration.total_seconds() * 1000
        elif self.definition.time_cycle is not None:
            raise NotImplementedError
        else:
            raise TypeError("Unsupported deadline")

    def validate(self):
        """Timers fire unconditionally at their deadline."""
        return True

    def prepare_for_execution(self, restart=False):
        """Schedule the deadline callback (honouring restart)."""
        self._push_callback(restart)

    def _callback(self):
        """Fire through the available work-item, else disarm."""
        if self.event._p_oid in callbacks:
            del callbacks[self.event._p_oid]

        if self.validate():
            wi = self.event._get_workitem()
            if wi is not None:
                self.event.start(None)
            else:
                self.event.stop()
        else:
            self._push_callback()

    def _push_callback(self, restart=False):
        """Compute the deadline and arm it through the after-commit hook."""
        deadline = self._start_time(restart)
        push_event_callback_after_commit(self.event, self._callback, (), deadline)

    def stop(self):
        # stop DelayedCallback
        """Cancel the scheduled callback through the reactor socket."""
        get_socket().send_pyobj(('stop', self.event._p_oid))
