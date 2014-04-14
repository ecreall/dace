import venusian
from zope.annotation.interfaces import IAnnotations, Interface
from zope.interface import implements, providedBy, implementedBy
from pyramid.exceptions import Forbidden
from pyramid.threadlocal import get_current_registry, get_current_request
from substanced.util import find_objectmap, get_content_type, find_catalog as fcsd, get_oid
from substanced.util import find_service as fssd
from .interfaces import (
        IEntity,
        IProcessDefinition,
        IDecisionWorkItem,
        IWorkItem,
        IObject,
        IBusinessAction)
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

    def __init__(self, name, provides=None, direct=False, **kw):
       self.name = name
       self.provides = provides
       self.direct = direct
       self.kw = kw

    def __call__(self, wrapped):
        def callback(scanner, name, ob):
            provides = self.provides
            if self.direct:
                component = ob
                if self.provides is None:
                    provides = list(implementedBy(component))[0]
            else:
                component = ob(**self.kw)
                if self.provides is None:
                    provides = list(providedBy(component))[0]

            scanner.config.registry.registerUtility(component, provides, self.name)

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


def find_service(name=None):
    resource = get_current_request().root
    return fssd(resource, name)


def allSubobjectsOfType(root = None, interface = None):
    root_oid = get_oid(root)
    if root is None or root == get_current_request().root:
        root_oid = 0

    if interface is None:
        interface = Interface

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


def subobjectsOfType(root = None, interface = None):
    root_oid = get_oid(root)
    if root is None or root == get_current_request().root:
        root_oid = 0

    if interface is None:
        interface = Interface

    interface_id = interface.__identifier__
    dace_catalog = find_catalog('dace')
    object_type_index = dace_catalog['object_type']
    container_oid_index = dace_catalog['container_oid']
    query = container_oid_index.eq(root_oid) & object_type_index.eq(interface_id)
    return [o for o in query.execute().all()]


def subobjectsOfKind(root = None, interface = None):
    root_oid = get_oid(root)
    if root is None or root == get_current_request().root:
        root_oid = 0

    if interface is None:
        interface = Interface

    interface_id = interface.__identifier__
    dace_catalog = find_catalog('dace')
    object_provides_index = dace_catalog['object_provides']
    container_oid_index = dace_catalog['container_oid']
    query = container_oid_index.eq(root_oid) & object_provides_index.any((interface_id,))
    return [o for o in query.execute().all()]


def get_current_process_uid(request):
    p_uid = request.params.get('p_uid', None)
#    if p_uid is not None:
#        request.response.setCookie('p_uid', p_uid)
#    else:
#        p_uid = request.cookies.get('p_uid', None)
    return p_uid
# TODO expire cookie when a form action succeeded
#    request.response.expireCookie('p_uid')
#    set the cookie in the update() of a form only

def getBusinessAction(process_id, node_id, behavior_id, request, context):
    global_request = get_current_request() 
    allactions = []
    dace_catalog = find_catalog('dace')
    process_id_index = dace_catalog['process_id']
    node_id_index = dace_catalog['node_id']
    #behavior_id_index = dace_catalog['behavior_id']
    context_id_index = dace_catalog['context_id']
    object_provides_index = dace_catalog['object_provides']
    query = process_id_index.eq(process_id) & \
            node_id_index.eq(node_id) & \
            object_provides_index.any((IBusinessAction.__identifier__,)) & \
            context_id_index.any(tuple([d.__identifier__ for d in context.__provides__.declared]))

    results = [w for w in query.execute().all()]
    if len(results) > 0:
        for action in results:
            if action.validate(context, global_request):
                allactions.append(action)

    registry = get_current_registry()
    pd = registry.getUtility(IProcessDefinition, process_id)
    # Add start workitem
    if not pd.isControlled and (not pd.isUnique or (pd.isUnique and not pd.isInstantiated)):
        wis = pd.start_process(node_id)
        for action in wis.actions:
            if action.validate(context, global_request) :
                allactions.append(action)

    if allactions:
        return allactions
    else:
        return None

def queryBusinessAction(process_id, node_id, behavior_id, request, context):
    return getBusinessAction(process_id, node_id, behavior_id,
                 request, context)

def getAllBusinessAction(context):
    global_request = get_current_request() 
    allactions = []
    dace_catalog = find_catalog('dace')
    context_id_index = dace_catalog['context_id']
    object_provides_index = dace_catalog['object_provides']
    query = object_provides_index.any((IBusinessAction.__identifier__,)) & \
            context_id_index.any(tuple([d.__identifier__ for d in context.__provides__.declared]))

    results = [a for a in query.execute().all()]
    if len(results) > 0:
        for action in results:
            if action.validate(context, global_request):
                allactions.append(action)

    registry = get_current_registry()
    allprocess = registry.getUtilitiesFor(IProcessDefinition)
    # Add start workitem
    for name, pd in allprocess:
        if not pd.isControlled and (not pd.isUnique or (pd.isUnique and not pd.isInstantiated)):
            wis = pd.start_process()
            for key in wis.keys():
                swisactions = wis[key].actions
                for action in swisactions:
                    if action.validate(context, global_request) :
                        allactions.append(action)

    return allactions

def getWorkItem(process_id, node_id, request, context,
                behavior_validator=lambda p, c: True):
    # If we previous call to getWorkItem was the same request
    # and returned a workitem from a gateway, search first in the
    # same gateway

    #annotations = IAnnotations(request)
    #workitems = annotations.get('workitems', None)
    #if workitems is not None:
    #    wi = workitems.get('%s.%s' % (process_id, node_id), None)
    #    if wi is not None and condition(wi.__parent__.__parent__, context):
    #        return wi

    # Not found in gateway, we search in catalog
    dace_catalog = find_catalog('dace')
    process_id_index = dace_catalog['process_id']
    node_id_index = dace_catalog['node_id']
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
                pass#process_ids = tuple(context.getInvolvedProcessIds())

    query =  process_id_index.eq(process_id) & \
            node_id_index.eq(process_id+'.'+node_id) & \
            object_provides_index.any((IWorkItem.__identifier__,))
    if process_ids: 
        query = query & process_inst_uid_index.any(process_ids)

    results = [w for w in query.execute().all()]
    if len(results) > 0:
        wi = None
        for wv in results:
            if wv.validate():
                wi = wv
                break

        if IDecisionWorkItem.providedBy(wi):
            gw = wi.__parent__
            #for workitem in gw.workitems:
                #workitems = annotations.setdefault('workitems', {})
                # TODO: I think node_id is a callable here, can't we just
                # use workitem[0].node_id?
                #from .catalog.interfaces import ISearchableObject
                #key = '%s.%s' % (process_id,
                #                 ISearchableObject(workitem[0]).node_id)
                #workitems[key] = workitem[0]
        if wi is None:
            raise Forbidden
        return wi

    # Not found in catalog, we return a start workitem
    if not pd.isControlled and (not pd.isUnique or (pd.isUnique and not pd.isInstantiated)):
        wi = pd.start_process(node_id)
        if wi is None:
            raise Forbidden
        else:
            #if not condition(None, context):
            #    raise Forbidden
            return wi

    raise Forbidden


def queryWorkItem(process_id, node_id, request, context):
    try:
        wi = getWorkItem(process_id, node_id,
                     request, context)
        return wi
    except Forbidden:
        return None


def workItemAvailable(menu_entry, process_id, node_id):
    try:
        wi = queryWorkItem(process_id, node_id,
                     menu_entry.request, menu_entry.context)
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
