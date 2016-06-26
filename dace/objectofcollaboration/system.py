# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Vincent Fretin, Amen Souissi

import transaction

from substanced.util import get_oid

from dace.processinstance.event import DelayedCallback
from dace.util import (
    find_catalog, getAllSystemActions,
    get_system_request, BaseJob)
from dace import log


last_transaction_by_machine = {}


def _call_action(action):
    transaction.begin()
    try:
        context = action.get_potential_context()
        if context is None:
            return

        request = get_system_request()
        request.invalidate_cache = True
        action.execute(context, request, {})
        log.info("Execute action %s", action.title)
        transaction.commit()
    except Exception as e:
        transaction.abort()
        log.exception(e)


def _get_cache_key():
    request = get_system_request()
    return str(get_oid(request.user))


def run():
    request = get_system_request()
    if request.user is None:
        # in test, db connection closed
        return

    catalog = find_catalog('dace')
    global last_transaction
    cache_key = _get_cache_key()
    last_transaction = last_transaction_by_machine.setdefault(cache_key, '')
    last_tid = catalog._p_jar.db().lastTransaction()
    if last_transaction != last_tid:
        last_transaction_by_machine[cache_key] = last_tid
        transaction.begin()
        try:
            system_actions = [a for a in getAllSystemActions()
                              if getattr(a, 'process', None)]
            log.info("new zodb transactions, actions to check: %s",
                     len(system_actions))
            for action in system_actions:
                _call_action(action)

        except Exception as e:
            log.exception(e)

        log.info("actions to check: done")

    run_crawler()


def run_crawler():
    """Start loop."""
    job = BaseJob('system')
    job.callable = run
    dc = DelayedCallback(job, 2000)
    dc.start()
