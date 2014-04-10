import time
import transaction
import datetime

from pyramid.threadlocal import get_current_registry

import zmq
from zmq.eventloop.ioloop import DelayedCallback
from zmq.eventloop.zmqstream import ZMQStream

from .core import FlowNode, BehavioralFlowNode, ProcessFinished
from dace.z3 import Job
from dace import log

# shared between threads
callbacks = {}


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
            callbacks[event._p_oid] = dc
            dc.start()

    transaction.get().addAfterCommitHook(after_commit_hook, args=(event, callback, callback_params, deadline, job))


class Event(BehavioralFlowNode, FlowNode):
    def __init__(self, process, definition, eventKind):
        super(Event, self).__init__(process, definition)
        self.eventKind = eventKind
        self.execution_prepared = False
        if eventKind:
            eventKind.event = self

    def __call__(self, transition):
        pass# pragma: no cover

    def prepare_for_execution(self):
        self.execution_prepared = True

    def start(self, transaction):
        wi = self._get_workitem()
        if wi is not None:
            super(Event, self).start(transaction)
            self.finish_behavior(wi)
        else:
            self.stop()

    def validate(self):
        pass# pragma: no cover

    def execute(self):
        pass# pragma: no cover

    def stop(self):
        self.setproperty('workitems', [])


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
            else:
                self.stop()
        else:
            self.stop()


class IntermediateThrowEvent(Throwing):
    pass# pragma: no cover


class IntermediateCatchEvent(Catching):
    pass# pragma: no cover


class EndEvent(Throwing):

    def prepare_for_execution(self):
        if not self.execution_prepared:
            super(Throwing, self).prepare_for_execution()
            if self.validate():
                wi = self._get_workitem()
                if wi is not None:
                    starttransaction = self.process.global_transaction.start_subtransaction('End', initiator=self)
                    self.start(starttransaction)
                    self.finish_behavior(wi)
                else:
                    self.stop()


    def finish_behavior(self, work_item):
        super(EndEvent, self).finish_behavior(work_item)
        if isinstance(self.eventKind, TerminateEvent):
            return
        # il faut supprimer les wi des subprocess aussi
        # gerer la suppression dans les noeuds... la suppression dans les subprocess est differente
        # Remove all workitems from process
        for node in self.process.nodes:
            node.stop()
            node.setproperty('workitems', [])

        self.process._finished = True
        registry = get_current_registry()
        registry.notify(ProcessFinished(self))
        # ici test pour les sous processus
        if self.process.definition.isSubProcess:
            self.process.attachedTo.finish_behavior(work_item)

        if self.process.definition.isVolatile:
            self.process.__parent__.delproperty('processes', self.process)


class EventKind(object):

    # cette operation est appelee par les evenements "Catching"
    def validate(self):
        return True

    def prepare_for_execution(self):
        pass# pragma: no cover

    # cette operation est appelee par les evenements "Throwing"
    def execute(self):
        pass# pragma: no cover

    def stop(self):
        pass# pragma: no cover

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
            del callbacks[self.event._p_oid]

        if self.validate():
            log.info('%s %s', self.event, "validate ok")
            wi = self._get_workitem()
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
    return 'tcp://*:12345'


class SignalEvent(EventKind):

    _msg = None

    def validate(self):
        return self.definition.refSignal(self.event.process) == self._msg

    def prepare_for_execution(self):
        ctx = get_zmq_context()
        s = ctx.socket(zmq.SUB)
        s.setsockopt(zmq.SUBSCRIBE, '')
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
                del callbacks[event_oid]

            job.args = (msg, )
            # wait 2s that the throw event transaction has committed
            dc = DelayedCallback(job, 2000)
            dc.start()

        callbacks[event_oid] = stream
        stream.on_recv(execute_next)

    def stop(self):
        if self.event._p_oid in callbacks:
            # Stop ZMQStream
            callbacks[self.event._p_oid].close()
            del callbacks[self.event._p_oid]

    def _callback(self, msg):
        self._msg = msg[0]
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
        time.sleep(1.0)
        s.send(ref)
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
            del callbacks[self.event._p_oid]
