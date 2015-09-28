# Copyright (c) 2014 by Ecreall under licence AGPL terms
# avalaible on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi

import time
import transaction
import datetime

from pyramid.threadlocal import get_current_registry

import zmq
from zmq.eventloop.zmqstream import ZMQStream

from .core import FlowNode, BehavioralFlowNode, ProcessFinished
from dace.util import (
    get_system_request,
    get_socket,
    DelayedCallback,
    get_zmq_context,
    EventJob)


callbacks = {}


def push_event_callback_after_commit(event, callback, callback_params, deadline):
    # Create job object now before the end of the interaction so we have
    # the logged in user.
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
            self.execution_prepared = False
        else:
            self.stop()

    def replay_path(self, decision, transaction):
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
        self.execution_prepared = False


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
                #self.finish_behavior(wi)
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
            request = get_system_request()
            root_process = current_process.attachedTo.process
            current_process.attachedTo.finish_execution(None, request)
            root_process.execution_context.remove_sub_execution_context(
                                          current_process.execution_context)
            parent_node = current_process.attachedTo.node
            if current_process in parent_node.sub_processes:
                parent_node.sub_processes.remove(current_process)

        if current_process.definition.isVolatile and \
           getattr(current_process, '__property__', None):
            getattr(current_process.__parent__.__class__,
                    current_process.__property__).remove(current_process.__parent__,
                                                      current_process)


class EventKind(object):

    # cette operation est appelee par les evenements "Catching"
    def validate(self):
        return True

    def prepare_for_execution(self, restart=False):
        pass # pragma: no cover

    # cette operation est appelee par les evenements "Throwing"
    def execute(self):
        pass # pragma: no cover

    def stop(self):
        pass # pragma: no cover

    @property
    def definition(self):
        return self.event.definition.eventKind



class ConditionalEvent(EventKind):

    def validate(self):
        return self.definition.condition(self.event.process)

    def prepare_for_execution(self, restart=False):
        self._push_callback()

    def _callback(self):
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
        push_event_callback_after_commit(self.event, self._callback, (), 1000)

    def stop(self):
        get_socket().send_pyobj(('stop', self.event._p_oid))


class TerminateEvent(EventKind):
    pass


# https://github.com/zeromq/pyzmq/blob/master/examples/poll/pubsub.py
# http://learning-0mq-with-pyzmq.readthedocs.org/en/latest/pyzmq/multisocket/tornadoeventloop.html

def get_signal_socket_url():
    return 'tcp://127.0.0.1:12346'


class Listener(object):
    def __init__(self, job, identifier):
        self.job = job
        self.identifier = identifier

    def start(self):
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

        ctx = get_zmq_context()
        s = ctx.socket(zmq.SUB)
        s.setsockopt_string(zmq.SUBSCRIBE, u'')
        s.connect(get_signal_socket_url())
        stream = ZMQStream(s)
        callbacks[identifier] = stream
        stream.on_recv(execute_next)


class SignalEvent(EventKind):

    _msg = None

    def validate(self):
        return self.definition.refSignal(self.event.process) == self._msg

    def prepare_for_execution(self, restart=False):
        job = EventJob('system')
        transaction.commit()  # needed to have self.event._p_oid
        job.callable = self._callback
        event_oid = self.event._p_oid
        listener = Listener(job, event_oid)
        get_socket().send_pyobj(('start', listener))

    def stop(self):
        # close ZMQStream
        get_socket().send_pyobj(('close', self.event._p_oid))

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
        s.bind(get_signal_socket_url())
        # Sleep to allow sockets to connect.
        time.sleep(0.2)
        s.send_string(ref)
        s.close()


class TimerEvent(EventKind):

    def __init__(self):
        super(TimerEvent, self).__init__()
        self.time_date = None
        self.time_duration = None
        self.time_cycle = None

    def _prepare_time(self, time, restart=False):
        if getattr(self, time, None) is None or not restart:
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
        return True

    def prepare_for_execution(self, restart=False):
        self._push_callback(restart)

    def _callback(self):
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
        deadline = self._start_time(restart)
        push_event_callback_after_commit(self.event, self._callback, (), deadline)

    def stop(self):
        # stop DelayedCallback
        get_socket().send_pyobj(('stop', self.event._p_oid))
