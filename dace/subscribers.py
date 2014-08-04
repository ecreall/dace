import signal
import threading
import zmq.eventloop.ioloop

import transaction
from pyramid.events import subscriber
from pyramid.interfaces import IApplicationCreated
from pyramid.testing import DummyRequest
from zope.processlifetime import DatabaseOpenedWithRoot
from zope.processlifetime import IDatabaseOpenedWithRoot

from . import log
from dace.objectofcollaboration.runtime import Runtime
from dace.objectofcollaboration.services.processdef_container import ProcessDefinitionContainer

from substanced.event import RootAdded
from substanced.util import find_service

from .interfaces import IWorkItem
from .processinstance.event import IntermediateCatchEvent
from .objectofcollaboration.system import start_crawler
from .objectofcollaboration.services.processdef_container import DEFINITIONS

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


@subscriber(IDatabaseOpenedWithRoot)
def start_intermediate_events(event):
    db = event.database
    app_root = db.open().root()['app_root']
    from substanced.util import find_catalog
    catalog = find_catalog(app_root, 'dace')
    query = catalog['object_provides'].any((IWorkItem.__identifier__,))
    results = query.execute().all()
    for wi in results:
        node = wi.node
        if isinstance(node, IntermediateCatchEvent):
            node.eventKind.prepare_for_execution()
            log.info("Calling %s.eventKind.prepare_for_execution()", node)
    # commit to execute after commit hooks
    transaction.commit()
#    start_crawler(app_root)
    app_root._p_jar.close()


@subscriber(RootAdded)
def add_catalogs(event):
    root = event.object
    catalogs = find_service(root, 'catalogs')
    catalogs.add_catalog('dace')
    root['runtime'] = Runtime(title='Runtime')


@subscriber(IApplicationCreated)
def application_created(event):
    """Called after config.make_wsgi_app()
    """
    registry = event.app.registry
    db = registry._zodb_databases['']
#    app = db.open().root().get('app_root')
    # Create app_root if it doesn't exist yet.
    request = DummyRequest()
    from substanced.db import root_factory
    event.app.root_factory = root_factory
    event.app.root_factory(request)
    # there is a commit done in root_factory if app_root was created
    registry.notify(DatabaseOpenedWithRoot(db))
