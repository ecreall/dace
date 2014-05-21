import time
import threading
import transaction
import datetime

from pyramid.threadlocal import get_current_registry, get_current_request

import zmq
from zmq.eventloop.ioloop import IOLoop
from zmq.eventloop.zmqstream import ZMQStream

from .core import FlowNode, BehavioralFlowNode, ProcessFinished
from dace.z3 import Job
from dace import log

# shared between threads
callbacks = {}
callbacks_lock = threading.Lock()

class DelayedCallback(object):
    """Schedule the given callback to be called once.

    The callback is called once, after callback_time milliseconds.

    `start` must be called after the DelayedCallback is created.

    The timeout is calculated from when `start` is called.
    """
    def __init__(self, callback, callback_time, io_loop=None):
        self.callback = callback
        self.callback_time = callback_time
        self.io_loop = io_loop or IOLoop.instance()
        self._timeout = None

    def start(self):
        """Start the timer."""
        def start_delayed_callback(dc):
            ioloop = IOLoop.current()
            dc._timeout = ioloop.add_timeout(
                ioloop.time() + self.callback_time / 1000.0, self.callback)
        self.io_loop.add_callback(start_delayed_callback, self)

    def stop(self):
        """Stop the timer."""
        if self._timeout is not None:
            def stop_delayed_callback(dc):
                ioloop = IOLoop.current()
                ioloop.remove_timeout(dc._timeout)
                dc._timeout = None
            self.io_loop.add_callback(stop_delayed_callback, self)


def push_callback_after_commit(event, callback, callback_params, deadline):
    # Create job object now before the end of the interaction so we have
    # the logged in user.
    job = Job()
    def after_commit_hook(status, *args, **kws):
        # status is true if the commit succeeded, or false if the commit aborted.
        if status:
            # Set callable now, we are sure to have p_oid
            event, callback, callback_params, deadline, job = args
            job.callable = callback
            job.args = callback_params
            dc = DelayedCallback(job, deadline)
            with callbacks_lock:
                callbacks[event._p_oid] = dc
            dc.start()

    transaction.get().addAfterCommitHook(after_commit_hook, args=(event, callback, callback_params, deadline, job))


class Event(BehavioralFlowNode, FlowNode):

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
        self.execution_prepared = True
        self.execution_finished = False

    def start(self, transaction):
        wi = self._get_workitem()
        if wi is not None:
            super(Event, self).start(transaction)
            self.execute()
            self.finish_behavior(wi)
            self.execution_finished = True
        else:
            self.stop()

    def replay_path(self, decision, transaction):
        if not self.execution_finished:
            self.execute()
            self.finish_behavior(decision)
            self.execution_finished = True

        super(Event, self).replay_path(decision, transaction)

    def validate(self):
        pass # pragma: no cover

    def execute(self):
        pass # pragma: no cover

    def stop(self):
        pass # pragma: no cover


class Throwing(Event):

    def validate(self):
        return True

    def prepare_for_execution(self):
        if not self.execution_prepared:
            super(Throwing, self).prepare_for_execution()
            if self.validate():
                self.start(None)
            else:
                self.stop()

    # l' operation est sans parametres (les parametres sont sur la definition est sont calculable)
    def execute(self):
        if self.eventKind is None:
            return

        return self.eventKind.execute()


class Catching(Event):

    def validate(self):
        if self.eventKind is None:
            return True

        return self.eventKind.validate()

    def prepare_for_execution(self):
        # If it's a empty StartEvent, execute the callback directly.
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
        super(Catching, self).stop()
        if self.eventKind is not None:
            self.eventKind.stop()


class StartEvent(Catching):

    def start(self, transaction):
        if not self.process._started:
            wi = self._get_workitem()
            if wi is not None:
                super(StartEvent, self).start(transaction)
                self.process.start()
                self.finish_behavior(wi)
                self.execution_finished = True
            else:
                self.stop()
        else:
            self.stop()


class IntermediateThrowEvent(Throwing):
    pass # pragma: no cover


class IntermediateCatchEvent(Catching):
    pass # pragma: no cover


class EndEvent(Throwing):


    def finish_behavior(self, work_item):
        super(EndEvent, self).finish_behavior(work_item)
        if isinstance(self.eventKind, TerminateEvent):
            return
        # Remove all workitems from process
        for node in self.process.nodes:
            node.stop()
            node.setproperty('workitems', [])

        self.process._finished = True
        registry = get_current_registry()
        registry.notify(ProcessFinished(self))
        if self.process.definition.isSubProcess:
            request = get_current_request()
            self.process.attachedTo.finish_execution(None, request)

        if self.process.definition.isVolatile:
            self.process.__parent__.__class__.properties[self.process.__property__]['del'](self.process.__parent__, self.process)


class EventKind(object):

    # cette operation est appelee par les evenements "Catching"
    def validate(self):
        return True

    def prepare_for_execution(self):
        pass # pragma: no cover

    # cette operation est appelee par les evenements "Throwing"
    def execute(self):
        pass # pragma: no cover

    def stop(self):
        pass # pragma: no cover

    @property
    def definition(self):
        return self.event.definition.eventKind


# C'est OK pour cette class rien a executer et rien a valider (la validation est dans le super)
class ConditionalEvent(EventKind):

    def validate(self):
        return self.definition.condition(self.event.process)

    def prepare_for_execution(self):
        self._push_callback()

    def _callback(self):
        if self.event._p_oid in callbacks:
            with callbacks_lock:
                del callbacks[self.event._p_oid]

        if self.validate():
            log.info('%s %s', self.event, "validate ok")
            wi = self.event._get_workitem()
            if wi is not None:
                self.event.start(None)
            else:
                self.stop()
        else:
            log.info('%s %s', self.event, "validate ko, retry in 1s")
            self._push_callback()

    def _push_callback(self):
        push_callback_after_commit(self.event, self._callback, (), 1000)

    def stop(self):
        if self.event._p_oid in callbacks:
            callbacks[self.event._p_oid].stop()
            with callbacks_lock:
                del callbacks[self.event._p_oid]


# C'est OK pour cette class rien a executer et rien a valider
class TerminateEvent(EventKind):
    pass


# https://github.com/zeromq/pyzmq/blob/master/examples/poll/pubsub.py
# http://learning-0mq-with-pyzmq.readthedocs.org/en/latest/pyzmq/multisocket/tornadoeventloop.html

_ctx = None

def get_zmq_context():
    global _ctx
    if _ctx is None:
        _ctx = zmq.Context()
    return _ctx


def get_socket_url():
    return 'tcp://127.0.0.1:12345'


class SignalEvent(EventKind):

    _msg = None

    def validate(self):
        return self.definition.refSignal(self.event.process) == self._msg

    def prepare_for_execution(self):
        ctx = get_zmq_context()
        s = ctx.socket(zmq.SUB)
        s.setsockopt_string(zmq.SUBSCRIBE, u'')
        s.connect(get_socket_url())
        stream = ZMQStream(s)
        job = Job()
        transaction.commit()  # needed to have self.event._p_oid
        job.callable = self._callback
        event_oid = self.event._p_oid
        def execute_next(msg):
            # We can't use zodb object from outside here because
            # this code is executed in another thread (eventloop)
            # We don't have site or interaction, so the job must be created
            # before.
            # we can't use push_callback_after_commit here because
            # it will never commit in this thread (eventloop)
            if event_oid in callbacks:
                callbacks[event_oid].close()
                with callbacks_lock:
                    del callbacks[event_oid]

            job.args = (msg, )
            # wait 2s that the throw event transaction has committed
            dc = DelayedCallback(job, 2000)
            dc.start()

        with callbacks_lock:
            callbacks[event_oid] = stream
        stream.on_recv(execute_next)

    def stop(self):
        if self.event._p_oid in callbacks:
            # Stop ZMQStream
            callbacks[self.event._p_oid].close()
            with callbacks_lock:
                del callbacks[self.event._p_oid]

    def _callback(self, msg):
        # convert str (py27) / bytes (py34) to unicode (py27) or str (py34)
        self._msg = msg[0].decode('utf-8')
        if self.validate():
            wi = self.event._get_workitem()
            if wi is not None:
                self.event.start(None)
            else:
                self.event.stop()

    def execute(self):
        ref = self.definition.refSignal(self.event.process)
        ctx = get_zmq_context()
        s = ctx.socket(zmq.PUB)
        s.bind(get_socket_url())
        # Sleep to allow sockets to connect.
        time.sleep(0.2)
        s.send_string(ref)
        s.close()


class TimerEvent(EventKind):

    def _start_time(self):
        """Return start time in milliseconds.
        """
        if self.definition.time_date is not None:
            deadline = self.definition.time_date(self.event.process)
            if not isinstance(deadline, datetime.datetime):
                raise TypeError("Unsupported deadline %r" % deadline)
            return (time.mktime(deadline.timetuple()) - time.time()) * 1000
        elif self.definition.time_duration is not None:
            deadline = self.definition.time_duration(self.event.process)
            if not isinstance(deadline, datetime.timedelta):
                raise TypeError("Unsupported deadline %r" % deadline)
            return deadline.total_seconds() * 1000
        elif self.definition.time_cycle is not None:
            raise NotImplementedError
        else:
            raise TypeError("Unsupported deadline %r" % deadline)

    def validate(self):
        return True

    def prepare_for_execution(self):
        self._push_callback()

    def _callback(self):
        if self.event._p_oid in callbacks:
            with callbacks_lock:
                del callbacks[self.event._p_oid]

        if self.validate():
            wi = self.event._get_workitem()
            if wi is not None:
                self.event.start(None)
            else:
                self.event.stop()
        else:
            self._push_callback()

    def _push_callback(self):
        deadline = self._start_time()
        push_callback_after_commit(self.event, self._callback, (), deadline)

    def stop(self):
        if self.event._p_oid in callbacks:
            # stop DelayedCallback
            callbacks[self.event._p_oid].stop()
            with callbacks_lock:
                del callbacks[self.event._p_oid]
