# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Vincent Fretin, Amen Souissi

import transaction

from substanced.util import get_oid

from dace.processinstance.event import DelayedCallback
from dace.util import find_catalog, getAllSystemActions, get_system_request
from dace.z3 import BaseJob
from dace import log


last_transaction_by_machine = {}


CRAWLERS = []


def _call_action(action, context):
    transaction.begin()
    request = get_system_request()# TDOD pyramid.testing.DummyRequest 
    try:
        action.execute(context, request, {})
        log.info("Execute action %s", action.title)
        transaction.commit()
    except Exception as e:
        transaction.abort()
        log.exception(e)


def _get_cache_key():
    request = get_system_request()
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
        system_actions = getAllSystemActions()
        log.info("new zodb transactions, actions to check: %s",
                 len(system_actions))
        for action in system_actions:
            context = None
            try:
                context = action.get_potential_context()
            except Exception:
                continue
            #getattr(action, '__parent__', None) is not None and \
            if context is not None:
                _call_action(action, context)

        log.info("checked")
        log.info("actions to check: done")
    run_crawler()


def run_crawler():
    """Start loop."""
    job = BaseJob()
    job.callable = run
    dc = DelayedCallback(job, 2000)
    dc.start()
    CRAWLERS.append(dc)
