import venusian
from zope.interface import Interface
from zope.interface import providedBy, implementedBy
from pyramid.exceptions import Forbidden
from pyramid.traversal import find_root
from pyramid.testing import DummyRequest
from pyramid.threadlocal import (
        get_current_registry, get_current_request, manager)
from substanced.interfaces import IUserLocator
from substanced.principal import DefaultUserLocator

from substanced.util import find_objectmap, find_catalog as fcsd, get_oid
from substanced.util import find_service as fssd
from .interfaces import (
        IEntity,
        IWorkItem,
        IBusinessAction)


def getSite(resource=None):
    request = get_current_request()
    if resource is not None:
        return find_root(resource)
    elif request is not None:
        return request.root

    return None


def get_obj(oid):
    root = getSite()
    objectmap = find_objectmap(root)
    obj = objectmap.object_for(oid)
    return obj


def find_catalog(name=None):
    resource = getSite()
    return fcsd(resource, name)


def find_service(name=None):
    resource = getSite()
    return fssd(resource, name)


def allSubobjectsOfType(root=None, interface=None):
    root_oid = get_oid(root)
    site = getSite(root)
    if root is None or root is site:
        root_oid = 0

    if interface is None:
        interface = Interface

    interface_id = interface.__identifier__
    dace_catalog = find_catalog('dace')
    object_type_index = dace_catalog['object_type']
    containers_oids_index = dace_catalog['containers_oids']
    query = containers_oids_index.any((root_oid,)) & object_type_index.eq(interface_id)
    return [o for o in query.execute().all()]


def allSubobjectsOfKind(root=None, interface=None):
    root_oid = get_oid(root)
    site = getSite(root)
    if root is None or root is site:
        root_oid = 0

    if interface is None:
        interface = Interface

    interface_id = interface.__identifier__
    dace_catalog = find_catalog('dace')
    object_provides_index = dace_catalog['object_provides']
    containers_oids_index = dace_catalog['containers_oids']
    query = containers_oids_index.any((root_oid,)) & object_provides_index.any((interface_id,))
    return [o for o in query.execute().all()]


def subobjectsOfType(root=None, interface=None):
    root_oid = get_oid(root)
    site = getSite(root)
    if root is None or root is site:
        root_oid = 0

    if interface is None:
        interface = Interface

    interface_id = interface.__identifier__
    dace_catalog = find_catalog('dace')
    object_type_index = dace_catalog['object_type']
    container_oid_index = dace_catalog['container_oid']
    query = container_oid_index.eq(root_oid) & object_type_index.eq(interface_id)
    return [o for o in query.execute().all()]


def subobjectsOfKind(root=None, interface=None):
    root_oid = get_oid(root)
    site = getSite(root)
    if root is None or root is site:
        root_oid = 0

    if interface is None:
        interface = Interface

    interface_id = interface.__identifier__
    dace_catalog = find_catalog('dace')
    object_provides_index = dace_catalog['object_provides']
    container_oid_index = dace_catalog['container_oid']
    query = container_oid_index.eq(root_oid) & object_provides_index.any((interface_id,))
    return [o for o in query.execute().all()]


def find_entities(interfaces=None, states=None, all_states_relation=False):
    if interfaces is None:
        interfaces = [IEntity]

    dace_catalog = find_catalog('dace')
    states_index = dace_catalog['object_states']
    object_provides_index = dace_catalog['object_provides']
    query = object_provides_index.any([i.__identifier__ for i in interfaces])
    if states is not None:
        if all_states_relation:
            query = query & states_index.all(states)
        else :
            query = query & states_index.any(states)

    entities = query.execute().all()
    return entities


def _acces_validation(context, request, validator, discriminator='Application'):
    dace_catalog = find_catalog('dace')
    context_id_index = dace_catalog['context_id']
    object_provides_index = dace_catalog['object_provides']
    isautomatic_index = dace_catalog['isautomatic']
    query = isautomatic_index.eq(True) & \
            object_provides_index.any((IBusinessAction.__identifier__,)) & \
            context_id_index.any(tuple([d.__identifier__ for d in context.__provides__.__iro__]))
    for a in query.execute().all():
        if validator(context, request, a):
            return True

    def_container = find_service('process_definition_container')
    definitions = [d for d in def_container.definitions if d.discriminator == discriminator]
    # Add start workitem
    for pd in definitions:
        if not pd.isControlled:
            wis = pd.start_process()
            if wis:
                for wi in wis.values():
                    actions = [a for a in wi.actions if a.isautomatic and a.context.__provides__(context)]
                    for a in actions:
                        if validator(context, request, a):
                            return True

    return False


acces_validation = _acces_validation


def get_current_process_uid(request):
    action_uid = request.params.get('action_uid', None)
    if action_uid is not None:
        return get_oid(get_obj(int(action_uid)).process)

    return None


def getBusinessAction(process_id, node_id, behavior_id, request, context):
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
            context_id_index.any(tuple([d.__identifier__ for d in context.__provides__.__iro__]))

    results = [w for w in query.execute().all()]
    if len(results) > 0:
        for action in results:
            try:
                action.validate(context, request)
                allactions.append(action)
            except Exception:
                continue

    def_container = find_service('process_definition_container')
    pd = def_container.get_definition(process_id)
    # Add start workitem
    if not pd.isControlled:
        s_wi = pd.start_process(node_id)
        if s_wi is not None:
            swisactions = s_wi.actions
            for action in swisactions:
                try:
                    action.validate(context, request)
                    allactions.append(action)
                except Exception:
                    continue

    if allactions:
        return allactions
    else:
        return None


def queryBusinessAction(process_id, node_id, behavior_id, request, context):
    return getBusinessAction(process_id, node_id, behavior_id,
                 request, context)


def getAllBusinessAction(context, request=None, isautomatic=False):
    if request is None:
        request = get_current_request()

    allactions = []
    dace_catalog = find_catalog('dace')
    context_id_index = dace_catalog['context_id']
    object_provides_index = dace_catalog['object_provides']
    query = object_provides_index.any((IBusinessAction.__identifier__,)) & \
            context_id_index.any(tuple([d.__identifier__ for d in context.__provides__.__iro__]))

    if isautomatic:
        isautomatic_index = dace_catalog['isautomatic']
        query = query & isautomatic_index.eq(True)

    results = [a for a in query.execute().all()]
    if len(results) > 0:
        for action in results:
            try:
                action.validate(context, request)
                allactions.append(action)
            except Exception:
                continue

    def_container = find_service('process_definition_container')
    allprocess = [(pd.id, pd) for pd in  def_container.definitions]

    # Add start workitem
    for name, pd in allprocess:
        if not pd.isControlled:
            wis = pd.start_process()
            if wis:
                for key in wis.keys():
                    swisactions = wis[key].actions
                    for action in swisactions:
                        if ((isautomatic and action.isautomatic) or not isautomatic):
                            try:
                                action.validate(context, request)
                                allactions.append(action)
                            except Exception:
                                continue

    return allactions


def getWorkItem(process_id, node_id, request, context,
                behavior_validator=lambda p, c: True):
    # If we previous call to getWorkItem was the same request
    # and returned a workitem from a gateway, search first in the
    # same gateway

    dace_catalog = find_catalog('dace')
    process_id_index = dace_catalog['process_id']
    node_id_index = dace_catalog['node_id']
    process_inst_uid_index = dace_catalog['process_inst_uid']
    object_provides_index = dace_catalog['object_provides']

    def_container = find_service('process_definition_container')
    pd = def_container.get_definition(process_id)
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

        if wi is None:
            raise Forbidden

        return wi

    # Not found in catalog, we return a start workitem
    if not pd.isControlled:
        wi = pd.start_process(node_id)
        if wi is None:
            raise Forbidden
        else:
            return wi

    raise Forbidden


def queryWorkItem(process_id, node_id, request, context):
    try:
        wi = getWorkItem(process_id, node_id,
                     request, context)
        return wi
    except Forbidden:
        return None


class Adapter(object):

    def __init__(self, context):
        self.context = context


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


import zope.copy
from dace.descriptors import (Descriptor, CompositeUniqueProperty,
        SharedUniqueProperty, CompositeMultipleProperty,
        SharedMultipleProperty)
from dace.relations import find_relations, connect
_marker = object()
OMIT_ATTRIBUTES = ('data', 'created_at', 'modified_at',
                   'dynamic_properties_def')

def copy(obj, container, new_name=None, shared_properties=False,
        composite_properties=False, roles=False,
        omit=OMIT_ATTRIBUTES):
    """Return a copy of obj

    If you need a deepcopy of the object, set composite_properties to True
    To copy the roles, set roles to True

    container can be a folder or a tuple (folder, propertyname)
    If this is a tuple, the new object will be set via propertyname.

(Pdb) pp obj.__dict__
{'__name__': u'object1',
 '__oid__': 4368702640781270144,
 '__parent__': <substanced.root.Root object None at 0x407cb18>,
 '__property__': None,
 '_composition_u_valuekey': u'object2',
 '_num_objects': <BTrees.Length.Length object at 0x4950758>,
 'created_at': datetime.datetime(2014, 9, 8, 13, 0, 11, 351214),
 'data': <BTrees.OOBTree.OOBTree object at 0x49513d0>,
 'dynamic_properties_def': {},
 'modified_at': datetime.datetime(2014, 9, 8, 13, 0, 11, 351227)}

(Pdb) pp new.__dict__
{'__property__': None,
 '_num_objects': <BTrees.Length.Length object at 0x46a6140>,
 'created_at': datetime.datetime(2014, 9, 8, 13, 6, 48, 635835),
 'data': <BTrees.OOBTree.OOBTree object at 0x46a1bd0>,
 'dynamic_properties_def': {},
 'modified_at': datetime.datetime(2014, 9, 8, 13, 6, 48, 635852)}
    """
    new = obj.__class__()
    # wake up object to have obj.__dict__ populated
    obj._p_activate()
    for key, value in obj.__dict__.items():
        if key.startswith('_') or key in omit:
            continue

        new_value = zope.copy.clone(value)
        # this does a new pickle for primitive value
        setattr(new, key, new_value)

    if new_name is None:
        new_name = 'copy_of_%s' % obj.__name__
    # we need to add it to a container so the object is indexed
    # and has a __oid__ attribute
    if isinstance(container, tuple):
        container, propertyname = container
        new.__name__ = new_name
        setattr(container, propertyname, new)
    else:
        container.add(new_name, new)

    seen = set()
    # We can have descriptors inherited,
    # so take care to not get descriptor of above classes if it has been
    # overriden in a subclass. This is what the seen variable is for here.
    for klass in obj.__class__.__mro__:
        for descriptor_id, descriptor in klass.__dict__.items():
            if descriptor_id in seen:
                continue

            seen.add(descriptor_id)
            if isinstance(descriptor, Descriptor):
                value = descriptor.__get__(obj)
                if not value:
                    continue

#                if isinstance(descriptor, (SharedUniqueProperty, SharedMultipleProperty)) and shared_properties:
#                    descriptor.__set__(new, value)  # this can have the side effect of moving value to a different container!
                # TODO do we really want to copy shared properties?
                if isinstance(descriptor, (CompositeUniqueProperty, CompositeMultipleProperty)) and composite_properties:
                    new_value = copy(value, (new, descriptor_id), new_name=value.__name__,
                            shared_properties=shared_properties,
                            composite_properties=composite_properties,
                            roles=roles)

                # copy roles
                if roles:
                    relations = find_relations(obj, {'target_id': get_oid(obj)})
                    for rel in relations:
                        source = rel.source
                        target = new
                        opts = {'reftype': rel.reftype, 'relation_id':
                                rel.relation_id, 'tags': list(rel.tags)}
                        connect(source, target, **opts)

    return new

def execute_callback(app, callback, login):
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
    callback()
    manager.pop()
