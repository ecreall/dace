from zope.annotation.interfaces import IAnnotations
from zope.i18n import translate
from zope.interface import Interface, providedBy, Declaration
from zope.location.interfaces import ILocation
from zope.security.interfaces import Forbidden
from pyramid.threadlocal import get_current_registry

from dace.util import Adapter, adapter, find_catalog
 
from .interfaces import (
        IEntity,
        IProcessDefinition,
        IStartWorkItem,
        IDecisionWorkItem,
        IWorkItem)
from .core import get_current_process_uid
from . import log, _


def getWorkItem(process_id, activity_id, request, context, condition=lambda p, c: True):
    # If we previous call to getWorkItem was the same request
    # and returned a workitem from a gateway, search first in the
    # same gateway

    annotations = IAnnotations(request)
    workitems = annotations.get('workitems', None)
    if workitems is not None:
        wi = workitems.get('%s.%s' % (process_id, activity_id), None)
        if wi is not None and condition(wi.__parent__.__parent__, context):
            return wi

    # Not found in gateway, we search in catalog
    searchableworkitem_catalog = find_catalog('searchableworkitem')
    objectprovides_catalog = find_catalog('objectprovidesindexes')

    process_id_index = searchableworkitem_catalog['process_id']
    activity_id_index = searchableworkitem_catalog['node_id']
    process_inst_uid_index = searchableworkitem_catalog['process_inst_uid']
    object_provides_index = objectprovides_catalog['object_provides']

    pd = get_current_registry().getUtility(IProcessDefinition, process_id)
    # Retrieve the same workitem we used to show the link
    p_uid = get_current_process_uid(request)
    process_ids = ()
    if p_uid is not None:
        process_ids = (int(p_uid),)
    else:
        # TODO: Do we need this?
        if IEntity.providedBy(context):
            filter_by_involved = True
            if filter_by_involved:
                process_ids = tuple(context.getInvolvedProcessIds())

    query = process_id_index.eq(process_id) &
            activity_id_index.eq(activity_id) & 
            object_provides_index.any((IWorkItem.__identifier__,)) & 
            process_inst_uid_index.any(process_ids)
    
    results = query.execute().all()
    if len(results) > 0:
        wi = None
        for wv in results:
            if wv.validate() and condition(wv.__parent__.__parent__ , context):
                wi = wv
                break

        if IDecisionWorkItem.providedBy(wi):
            gw = wi.__parent__
            for workitem in gw.workitems.values():
                workitems = annotations.setdefault('workitems', {})
                # TODO: I think node_id is a callable here, can't we just
                # use workitem[0].node_id?
                key = '%s.%s' % (process_id,
                                 ISearchableWorkItem(workitem[0]).node_id)
                workitems[key] = workitem[0]
        if wi is None:
            raise Forbidden
        return wi

    # Not found in catalog, we return a start workitem
    if not pd.isControlled and (not pd.isUnique or (pd.isUnique and not pd.isInstantiated)):
        wi = pd.createStartWorkItem(activity_id)
        if wi is None:
            raise Forbidden
        else:
            if not condition(None, context):
                raise Forbidden
            return wi

    raise Forbidden


def queryWorkItem(process_id, activity_id, request, context, condition=lambda p, c: True):
    try:
        wi = getWorkItem(process_id, activity_id,
                     request, context, condition)
        return wi
    except Forbidden:
        return None


def workItemAvailable(menu_entry, process_id, activity_id, condition=lambda p, c: True):
    try:
        wi = queryWorkItem(process_id, activity_id,
                     menu_entry.request, menu_entry.context, condition)
        if wi is None:
            return False

        if wi.is_locked(menu_entry.request):
            menu_entry.title = translate(menu_entry.title, context=menu_entry.request) + \
                               translate(_(u" (locked)"), context=menu_entry.request)
        p_uid = ISearchableWorkItem(wi).process_inst_uid()
        if p_uid:
            menu_entry.params = {'p_uid': p_uid[0]}
    except Exception as e:
        log.exception(e)
        return False
    return True
