import signal
import threading
import zmq.eventloop.ioloop

import transaction

from . import log


class ConsumeTasks(threading.Thread):

    def run(self):
        # TODO: configure logging
        loop = zmq.eventloop.ioloop.IOLoop.instance()
        loop.start()

    def stop(self):
        loop = zmq.eventloop.ioloop.IOLoop.instance()
        loop.stop()

consumetasks = None


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

from ZODB.broken import Broken
#from zope.app.appsetup.bootstrap import getInformationFromEvent
from zope.component import getUtility
from zope.component.hooks import getSite, setSite
#from zope.intid.interfaces import IIntIds
from .interfaces import IWorkItem
from .event import IntermediateCatchEvent
from .system import start_crawler


def start_intermediate_events(event):
    db, connection, root, root_folder = getInformationFromEvent(event)
    apps = list(root_folder.values())
    old_site = getSite()
    for app in root_folder.values():
        setSite(app)
        catalog = getUtility(ICatalog)
        intids = getUtility(IIntIds)
        query = {'object_provides': {'any_of': (IWorkItem.__identifier__,)},
        }
        results = catalog.apply(query)
        for w in results:
            wi = intids.getObject(w)
            if isinstance(wi, Broken):
                if app in apps:
                    apps.remove(app)
                continue
            node = wi.node
            if isinstance(node, IntermediateCatchEvent):
                node.eventKind.prepare()
                log.info("Calling %s.eventKind.prepare()", node)
    setSite(old_site)
    # commit to execute after commit hooks
    transaction.commit()

    for app in apps:
        start_crawler(app)


def start_machine(event):
    db, connection, root, root_folder = getInformationFromEvent(event)
    apps = list(root_folder.values())
    # TODO: get app_id and login parameters from the ini file or command line
    start_ioloop(event)
    for app in apps:
        start_crawler(app, "ben")



from pyramid.events import subscriber

from substanced.event import RootAdded, ObjectAdded
from substanced.util import find_service, set_oid , find_objectmap, get_oid
from dace.util import find_catalog
from pyramid.threadlocal import get_current_request


@subscriber(RootAdded)
def add_catalogs(event):
    root = event.object
    catalogs = find_service(root, 'catalogs')
    catalog = catalogs.add_catalog('dace')
