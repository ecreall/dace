import transaction

from pyramid.testing import DummyRequest
from pyramid.threadlocal import (
        get_current_registry, get_current_request, manager)
from substanced.interfaces import IUserLocator
from substanced.principal import DefaultUserLocator
from substanced.util import get_oid

from dace.interfaces import IEntity, IBusinessAction
from dace.processinstance.event import DelayedCallback
from dace.util import find_catalog
from dace.z3 import BaseJob
from dace import log

last_transaction_by_machine = {}
CRAWLERS = []


def _call_action(action, context):
    transaction.begin()
    request = get_current_request()
    try:
        action.action.execute(context, request, {})  #TODO AttributeError: 'WorkItem' object has no attribute 'execute'
        log.info("Execute action %s", action.title)
        transaction.commit()
    except Exception as e:
        transaction.abort()
        log.exception(e)


def _get_cache_key():
    request = get_current_request()
    return str(get_oid(request.user))
#    from dace.objectofcollaboration.principal.util import get_current
#    return str(get_oid(get_current()))#request.user))


def run():
    catalog = find_catalog('dace')
    global last_transaction
    cache_key = _get_cache_key()
    last_transaction = last_transaction_by_machine.setdefault(cache_key, '')
    last_tid = catalog._p_jar.db().lastTransaction()
    if last_transaction != last_tid:
        last_transaction_by_machine[cache_key] = last_tid
        transaction.begin()
    #            query = {'object_provides': {'any_of': (IBusinessAction.__identifier__,)}}
    #            results = list(catalog.apply(query))
    #            print "actions to check:", len(results)
    #            continue
        query = catalog['object_provides'].any((IEntity.__identifier__,))
        results = list(query.execute().all())
        log.info("new zodb transactions, objects to check: %s", len(results))

        for content in results:
            continue  # TODO remove this line and fix _call_action
            for action in content.actions:
                if getattr(action.action, '__parent__', None) is None:
                    # action.action.workitem is a StartWorkitem
                    continue

                # DecisionWorkItem may have been removed
                # action.action.__parent__ is the workitem
                # if decision workitem was removed, so the actions
#                if getattr(action.action.__parent__, '_v_removed', False):
#                    continue

                _call_action(action, content)
        log.info("checked")
        #log.info("objects to check: done")
    run_crawler()


def run_crawler():
    job = BaseJob()
    job.callable = run
    dc = DelayedCallback(job, 2000)
    dc.start()
    CRAWLERS.append(dc)


def start_crawler(app, login="system"):
    """Start loop."""
    # set site and interaction that will be memorized in job
    request = DummyRequest()
    request.root = app
    registry = get_current_registry()
    manager.push({'registry': registry, 'request': request})
    locator = registry.queryMultiAdapter((app, request),
                                              IUserLocator)
    if locator is None:
        locator = DefaultUserLocator(app, request)

    user = locator.get_user_by_login(login)
    request.user = user
    run_crawler()
    manager.pop()
