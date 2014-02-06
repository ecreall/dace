import threading
import transaction
from zope.authentication.interfaces import IAuthentication
from zope.component import getUtility
from zope.component.hooks import setSite
from zope.security.management import (
    endInteraction, newInteraction, restoreInteraction, queryInteraction)
from zope.intid.interfaces import IIntIds
from zope.catalog.interfaces import ICatalog
from zope.component.hooks import getSite
from zmq.eventloop.ioloop import DelayedCallback

from .interfaces import IEntity, IBusinessAction
from .z3 import BaseJob, Participation
from . import log

last_transaction_by_app = threading.local()


def _call_action(action):
    transaction.begin()
    try:
        action.action.__parent__.start()
        log.info("Execute action %s", action)
        transaction.commit()
    except Exception as e:
        transaction.abort()
        log.exception(e)


def _get_cache_key():
    site_id = getSite().__name__
    interaction = queryInteraction()
    participants = tuple(
                participation.principal.id for participation in
                interaction.participations)
    return '_'.join((site_id, ) + participants)


def run():
    catalog = getUtility(ICatalog)
    global last_transaction
    cache_key = _get_cache_key()
    last_transaction = getattr(last_transaction_by_app, cache_key, None)
    last_tid = catalog._p_jar.db().lastTransaction()
    if last_transaction != last_tid:
        setattr(last_transaction_by_app, cache_key, last_tid)
        intids = getUtility(IIntIds)
        transaction.begin()
    #            query = {'object_provides': {'any_of': (IBusinessAction.__identifier__,)}}
    #            results = list(catalog.apply(query))
    #            print "actions to check:", len(results)
    #            continue
        query = {'object_provides': {'any_of': (IEntity.__identifier__,)}}
        results = list(catalog.apply(query))
        log.info("objects to check: %s", len(results))

        for intid in results:
            content = intids.getObject(intid)
            for action in content.actions:
                # DecisionWorkItem may have been removed
                # action.action.__parent__ is the workitem
                # if decision workitem was removed, so the actions
                if getattr(action.action.__parent__, '_v_removed', False):
                    continue

                _call_action(action)
        log.info("objects to check: done")
    run_crawler()


def run_crawler():
    job = BaseJob()
    job.callable = run
    dc = DelayedCallback(job, 2000)
    dc.start()


def start_crawler(app, login="system"):
    """Start loop."""
    # commit to be sure the application exists in the thread
    transaction.commit()
    # set site and interaction that will be memorized in job
    old_site = getSite()
    endInteraction()

    setSite(app)
    auth = getUtility(IAuthentication)
    newInteraction(
        *(Participation(auth.getPrincipal(principal_id)) for
          principal_id in [login]))
    run_crawler()

    restoreInteraction()
    setSite(old_site)
