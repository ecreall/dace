# Copyright (c) 2014 by Ecreall under licence AGPL terms
# avalaible on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Vincent Fretin, Amen Souissi

import pickle
import signal
import threading
import zmq
from zmq.eventloop.ioloop import IOLoop
from zmq.eventloop.zmqstream import ZMQStream

import transaction
from pyramid.events import subscriber
from pyramid.threadlocal import (
    get_current_registry, manager)

from . import log
from dace.objectofcollaboration.runtime import Runtime

from substanced.event import RootAdded
from substanced.util import find_service

from dace.interfaces import IWorkItem
from dace.processinstance.event import (
    IntermediateCatchEvent)
from dace.objectofcollaboration.principal import Machine
from dace.objectofcollaboration.principal.util import grant_roles
from dace.objectofcollaboration.system import run_crawler
from dace.util import execute_callback, find_catalog, get_socket_url
from dace.processinstance import event as event_mod


class ConsumeTasks(threading.Thread):
    terminated = False
    def __init__(self, registry, event):
        threading.Thread.__init__(self)
        self.registry = registry
        self.event = event

    def run(self):
        if self.terminated:
            return

        manager.push({'registry': self.registry, 'request': None})
        loop = IOLoop.instance()
        ctx = zmq.Context()
        def callback():
            s = ctx.socket(zmq.PULL)
            s.setsockopt(zmq.LINGER, 0)
            s.bind(get_socket_url())
            def execute_next(action):
                # action is a list with one pickle
                method, obj = pickle.loads(action[0])
                # obj can be an oid, dc (DelayedCallback object) or
                # Listener object
                if method in ('stop', 'close', 'ack'):
                    oid = obj
                    dc = event_mod.callbacks.get(oid, None)
                    if dc is not None:
                        if method != 'ack':
                            getattr(dc, method)()

                        del event_mod.callbacks[oid]
                else:
                    # system crawler doesn't have an identifier
                    # and so the DelayedCallback started from a SignalEvent
                    if obj.identifier is not None:
                        event_mod.callbacks[obj.identifier] = obj

                    getattr(obj, method)()

            self.stream = ZMQStream(s)
            self.stream.on_recv(execute_next)

        # It's ok to not use loop.add_callback
        # (the only method that is thread safe)
        # because the loop as not started yet
        loop.add_timeout(loop.time() + 2, callback)

        db = self.event.database
        root = db.open().root()['app_root']
        start_intermediate_events(root)
        root._p_jar.close()
        try:
            loop.start()
        except zmq.ZMQError:
            # only needed for tests isolation
            # we go here only if we try to close the stream in the stop method
            # below
            loop._callbacks = []
            loop._timeouts = []
            raise

    def stop(self):
        self.terminated = True
        loop = IOLoop.instance()
        with loop._callback_lock:
            for timeout in loop._timeouts:
                timeout.callback = None

        for dc_or_stream in event_mod.callbacks.values():
            if hasattr(dc_or_stream, 'close'):
                def close_stream_callback(stream):
                    stream.close()

                loop.add_callback(close_stream_callback, dc_or_stream)
            else:
                dc_or_stream.stop()

        event_mod.callbacks = {}

#        if getattr(self, 'stream', None) is not None:
#            self.stream.close()

        with loop._callback_lock:
            for timeout in loop._timeouts:
                timeout.callback = None

        loop.stop()


consumetasks = None
curr_sigint_handler = signal.getsignal(signal.SIGINT)


def sigint_handler(*args):
    stop_ioloop()
    curr_sigint_handler(*args)

# executed when 'system' app is started
def start_ioloop(event):
    """Start loop."""
    signal.signal(signal.SIGINT, sigint_handler)
    global consumetasks
    if consumetasks is None:
        registry = get_current_registry()
        consumetasks = ConsumeTasks(registry, event)
        consumetasks.start()


def stop_ioloop():
    global consumetasks
    if consumetasks is not None:
        consumetasks.stop()
        consumetasks.join(3)
        consumetasks = None


def start_intermediate_events_callback():
    catalog = find_catalog('dace')
    query = catalog['object_provides'].any((IWorkItem.__identifier__,))
    results = query.execute().all()
    for wi in results:
        node = wi.node
        if isinstance(node, IntermediateCatchEvent):
            if node.execution_prepared:
                node.eventKind.prepare_for_execution(True)
            log.info("Calling %s.eventKind.prepare_for_execution()", node)
    # commit to execute after commit hooks
    transaction.commit()


def start_intermediate_events(root):
    if 'system' in root['principals']['users']:
        execute_callback(root, start_intermediate_events_callback, 'system')
        execute_callback(root, run_crawler, 'system')


def add_system_machine(root):
    system = Machine('system')
    root['principals']['users']['system'] = system
    grant_roles(system, ('System',), root=root)


@subscriber(RootAdded)
def add_catalogs(event):
    root = event.object
    catalogs = find_service(root, 'catalogs')
    catalogs.add_catalog('dace')
    root['runtime'] = Runtime(title='Runtime')
    add_system_machine(root)
