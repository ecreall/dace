# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Vincent Fretin, Amen Souissi

"""The system crawler: executes the pending system actions.

``run`` wakes every 2 s (``run_crawler`` re-arms a ``DelayedCallback``
through the reactor), but only works when the ZODB has *new
transactions* since the last visit (per machine): it then collects the
system actions (``getAllSystemActions``) bound to a process or offered
by a start work-item, and executes each in its own transaction against
its ``get_potential_context()``.
"""
import transaction

from substanced.util import get_oid

from dace.processinstance.event import DelayedCallback
from dace.util import (
    find_catalog, getAllSystemActions,
    get_system_request, BaseJob)
from dace import log


last_transaction_by_machine = {}


def _call_action(action):
    """Execute one system action against its potential context (own transaction)."""
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
    """Per-machine key of the last-seen ZODB transaction id."""
    request = get_system_request()
    return str(get_oid(request.user))


def run():
    """One crawler pass (see module docstring), then re-arm."""
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
                              if getattr(a, 'process', None) or
                              a.isstart]
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
