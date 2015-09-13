# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Vincent Fretin, Amen Souissi

import signal
import threading
import zmq.eventloop.ioloop

import transaction
from pyramid.events import subscriber
from pyramid.interfaces import IApplicationCreated
from pyramid.testing import DummyRequest
from pyramid.threadlocal import manager
from zope.processlifetime import DatabaseOpenedWithRoot, IDatabaseOpenedWithRoot

from . import log
from dace.objectofcollaboration.runtime import Runtime

from substanced.event import RootAdded
from substanced.util import find_service

from dace.interfaces import IWorkItem
from dace.processinstance.event import IntermediateCatchEvent
from dace.objectofcollaboration.principal import Machine
from dace.objectofcollaboration.principal.util import grant_roles
from dace.objectofcollaboration.system import run_crawler
from dace.util import execute_callback, find_catalog


class ConsumeTasks(threading.Thread):

    def run(self):
        # TODO: configure logging
        loop = zmq.eventloop.ioloop.IOLoop.instance()
        # we need to write a pdb here to activate a pdb in a Job...
        loop.start()

    def stop(self):
        loop = zmq.eventloop.ioloop.IOLoop.instance()
        loop.stop()


consumetasks = None


@subscriber(IDatabaseOpenedWithRoot)
def start_ioloop(event):
    """Start loop."""
    global consumetasks
    if consumetasks is None:
        consumetasks = ConsumeTasks()
        consumetasks.setDaemon(True)
        consumetasks.start()


def stop_ioloop():
    global consumetasks
    if consumetasks is not None:
        consumetasks.stop()
        consumetasks.join(3)
        consumetasks = None


curr_sigint_handler = signal.getsignal(signal.SIGINT)



def sigint_handler(*args):
    stop_ioloop()
    curr_sigint_handler(*args)


signal.signal(signal.SIGINT, sigint_handler)


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


@subscriber(IDatabaseOpenedWithRoot)
def start_intermediate_events(event):
    db = event.database
    app_root = db.open().root()['app_root']
    if 'system' in app_root['principals']['users']:
        execute_callback(app_root, start_intermediate_events_callback, 'system')
        execute_callback(app_root, run_crawler, 'system')

    app_root._p_jar.close()


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


@subscriber(IApplicationCreated)
def application_created(event):
    """Called after config.make_wsgi_app()
    """
    registry = event.app.registry
    db = registry._zodb_databases['']
    # Create app_root if it doesn't exist yet.
    request = DummyRequest()
    manager.push({'registry': registry, 'request': request})
    from substanced.db import root_factory
    event.app.root_factory = root_factory
    event.app.root_factory(request)
    # there is a commit done in root_factory if app_root was created
    registry.notify(DatabaseOpenedWithRoot(db))
    manager.pop()
