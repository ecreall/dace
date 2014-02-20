import venusian
from zope.annotation.interfaces import IAnnotations, Interface
from pyramid.exceptions import Forbidden
from pyramid.threadlocal import get_current_registry, get_current_request
from substanced.util import find_objectmap, get_content_type, get_oid, find_catalog as fcsd

from .interfaces import (
        IEntity,
        IProcessDefinition,
        IDecisionWorkItem,
        IWorkItem)
from . import log


class Adapter(object):

    def __init__(self, context):
        self.context = context


def get_obj(oid):
    request = get_current_request()
    objectmap = find_objectmap(request.root)
    obj = objectmap.object_for(oid)
    return obj


class utility(object):

    def __init__(self, name):
       self.name = name

    def __call__(self, wrapped):
        def callback(scanner, ob, name=u''):
            instance = ob()
            scanner.config.registry.registerUtility(component=instance, name=self.name)

        venusian.attach(wrapped, callback)
        return wrapped


class adapter(object):

    def __init__(self, context, name=u''):
       self.context = context
       self.name = name

    def __call__(self, wrapped):
        def callback(scanner, name, ob):
            mprovided = list(ob.__implemented__.interfaces())[0]
            scanner.config.registry.registerAdapter(factory=ob, required=(self.context,), provided=mprovided, name=self.name)

        venusian.attach(wrapped, callback)
        return wrapped


def find_catalog(name=None):
    resource = get_current_request().root
    return fcsd(resource, name)


def allSubobjectsOfType(root = None, interface = None):
    root_oid =  0
    if root is None:
        root = get_current_request().root
    else :
        root_oid =  get_oid(root)

    if interface is None:
        interface = Interface

    root_oid =  get_oid(root)
    interface_id = interface.__identifier__
    dace_catalog = find_catalog('dace')
    object_type_index = dace_catalog['object_type']
    containers_oids_index = dace_catalog['containers_oids']
    query = containers_oids_index.any((root_oid,)) & object_type_index.eq(interface_id)
    return [o for o in query.execute().all()]


def allSubobjectsOfKind(root = None, interface = None):
    root_oid = get_oid(root)
    if root is None or root == get_current_request().root:
        root_oid = 0

    if interface is None:
        interface = Interface

    interface_id = interface.__identifier__
    dace_catalog = find_catalog('dace')
    object_provides_index = dace_catalog['object_provides']
    containers_oids_index = dace_catalog['containers_oids']
    query = containers_oids_index.any((root_oid,)) & object_provides_index.any((interface_id,))
    return [o for o in query.execute().all()]


def get_current_process_uid(request):
    p_uid = request.form.get('p_uid', None)
#    if p_uid is not None:
#        request.response.setCookie('p_uid', p_uid)
#    else:
#        p_uid = request.cookies.get('p_uid', None)
    return p_uid
# TODO expire cookie when a form action succeeded
#    request.response.expireCookie('p_uid')
#    set the cookie in the update() of a form only


def getWorkItem(process_id, activity_id, request, context,
                condition=lambda p, c: True):
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
    dace_catalog = find_catalog('dace')
    process_id_index = dace_catalog['process_id']
    activity_id_index = dace_catalog['node_id']
    process_inst_uid_index = dace_catalog['process_inst_uid']
    object_provides_index = dace_catalog['object_provides']

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

    query = process_id_index.eq(process_id) & \
            activity_id_index.eq(activity_id) & \
            object_provides_index.any((IWorkItem.__identifier__,)) & \
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
                from .catalog.interfaces import ISearchableObject
                key = '%s.%s' % (process_id,
                                 ISearchableObject(workitem[0]).node_id)
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

#        if wi.is_locked(menu_entry.request):
#            menu_entry.title = translate(menu_entry.title, context=menu_entry.request) + \
#                               translate(_(u" (locked)"), context=menu_entry.request)
        from .catalog.interfaces import ISearchableObject
        p_uid = ISearchableObject(wi).process_inst_uid()
        if p_uid:
            menu_entry.params = {'p_uid': p_uid[0]}
    except Exception as e:
        log.exception(e)
        return False
    return True
