from zope.annotation.interfaces import IAnnotations
from zope.catalog.interfaces import ICatalog
from zope.component import getUtility
from zope.i18n import translate
from zope.intid.interfaces import IIntIds
from zope.interface import Interface, providedBy, Declaration
from zope.location.interfaces import ILocation
from zope.security.interfaces import Forbidden

from dace.util import Adapter, adapter

import grok
from grok import index

from dolmen.app.site import IDolmen
 
from .interfaces import (
        IEntity,
        IProcessDefinition,
        IStartWorkItem,
        IDecisionWorkItem,
        IWorkItem)
from .core import get_current_process_uid
from . import log, _


from substanced.catalog import (
    catalog_factory,
    Text,
    Field,
    )

class IObjectProvides(Interface):
    def object_provides():
        pass

@catalog_factory('objectprovidesindexes')
class ObjectProvidesIndexes(object):
    #grok.context(IObjectProvides)

    object_provides = Set()

@adapter(context = ILocation, name = u'objectprovides' )
class ObjectProvides(Adapter):
    """Return provided interfaces of the object.
    """
    grok.implements(IObjectProvides)

    def object_provides(self):
        return [i.__identifier__ for i in providedBy(self.context).flattened()]


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
    catalog = getUtility(ICatalog)
    intids = getUtility(IIntIds)
    query = {
             'object_provides': {'any_of': (IWorkItem.__identifier__,)},
             'process_id': (process_id, process_id),
             'node_id': (activity_id, activity_id),
    }

    pd = getUtility(IProcessDefinition, process_id)
    # Retrieve the same workitem we used to show the link
    p_uid = get_current_process_uid(request)
    if p_uid is not None:
        query['process_inst_uid'] = {'any_of': (int(p_uid),)}
    else:
        # TODO: Do we need this?
        if IEntity.providedBy(context):
            filter_by_involved = True
            if filter_by_involved:
                process_ids = tuple(context.getInvolvedProcessIds())
                if process_ids:
                    query['process_inst_uid'] = {'any_of': process_ids}

    results = list(catalog.apply(query))
    if len(results) > 0:
        wi = None
        for w in results:
            wv = intids.getObject(w)
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
