# Copyright (c) 2014 by Ecreall under licence AGPL terms
# avalaible on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi

from __future__ import print_function

import sys
import time
import rwproperty
import unicodedata
import venusian
import zope.copy
import transaction
import zmq
import transaction
from zmq.eventloop.ioloop import IOLoop
from zope.interface import providedBy, implementedBy, Interface
from ZODB.interfaces import IBroken
from ZODB.POSException import ConflictError
from pyramid.exceptions import Forbidden
from pyramid.traversal import find_root
from pyramid.testing import DummyRequest
from pyramid.threadlocal import (
    get_current_registry, get_current_request, manager)

from substanced.interfaces import IUserLocator
from substanced.principal import DefaultUserLocator
from substanced.util import (
    find_objectmap,
    find_catalog as fcsd,
    get_oid,
    find_service as fssd,
    BrokenWrapper)

from dace.interfaces import (
    IEntity,
    IWorkItem,
    IBusinessAction)
from dace.descriptors import (
    Descriptor, CompositeUniqueProperty, CompositeMultipleProperty)
from dace.relations import find_relations, connect
from dace import _


class BaseJob(object):
    # a job that examines the site and interaction participants when it is
    # created, and reestablishes them when run, tearing down as necessary.

    args = ()

    def __init__(self, login=None):
        request = get_current_request()
        self.site_id = 'app_root'
        self.database_name = request.root._p_jar.db().database_name
        if login is not None:
            user = get_user_by_login(login)
        else:
            user = request.user
        self.userid = get_oid(user)

    def retry(self):
        transaction.begin()
        self.callable(*self.args)
        transaction.commit()

    def __call__(self):
        # log here don't work, we are in the eventloop
        try:
            app = self.setUp()
            self.retry()
        except ConflictError:
            transaction.abort()
            print("ConflictError, retry in 2s")
            time.sleep(2.0)
            self.retry()
        except Exception:
            transaction.abort()
            print("transaction abort, so retry aborted")
            print(sys.exc_info())
            print(self.callable)
            raise
        finally:
            self.tearDown(app)

    def setUp(self):
        registry = get_current_registry()
        db = registry._zodb_databases[self.database_name]
        app = db.open().root()[self.site_id]
        request = DummyRequest()
        request.root = app
        manager.push({'registry': registry, 'request': request})
        user = get_user_by_userid(self.userid)
        request.user = user
        return app

    def tearDown(self, app):
        manager.pop()
        app._p_jar.close()


class Job(BaseJob):

    def __init__(self, callable, login=None):
        super(Job, self).__init__(login)
        self.callable = callable
        self._kwargs = {}

    @rwproperty.setproperty
    def kwargs(self, value):
        def get_value(obj):
            return getattr(obj, '_p_oid', obj)

        self._kwargs = {key: get_value(obj) for key, obj in value.items()}

    def retry(self):
        request = get_current_request()
        site = request.root
        def get_value(obj):
            try:
                result = site._p_jar.get(obj)
                return result if result is not None else obj
            except:
                return obj

        kwargs = {key: get_value(obj) for key, obj in self._kwargs.items()}
        transaction.begin()
        self.callable(**kwargs)
        transaction.commit()


class EventJob(BaseJob):
    _callable_oid = _callable_name = None

    @property
    def callable(self):
        request = get_current_request()
        site = request.root
        callable_root = site._p_jar.get(self._callable_oid).eventKind
        call = getattr(callable_root, self._callable_name)
        return call

    @rwproperty.setproperty
    def callable(self, value):
        self._callable_oid = value.__self__.event._p_oid
        self._callable_name = value.__name__


def get_system_request():
    request = get_current_request()
    if isinstance(request, DummyRequest) and \
       not hasattr(request, 'is_system_request'):
        registry = get_current_registry()
        application_url = registry.settings.get('application.url', None)
        if application_url:
            request.url = application_url
            request.path_url = application_url
            request.host_url = application_url
            request.application_url = application_url
            request.is_system_request = True

    return request


def is_broken(resource):
    return isinstance(resource, BrokenWrapper) or \
           IBroken.providedBy(resource)


def name_chooser(container={}, name='default_name'):
    # remove characters that checkName does not allow
    try:
        name = str(name)
    except:
        name = ''
    name = name.replace('/', '-').lstrip('+@')
    # for an existing name, append a number.
    # We should keep client's os.path.extsep (not ours), we assume it's '.'
    dot = name.rfind('.')
    if dot >= 0:
        suffix = name[dot:]
        name = name[:dot]
    else:
        suffix = ''

    unicodedname = unicodedata.normalize('NFKD',
                                         u''+name).encode('ascii',
                                                          'ignore').decode()
    new_name = unicodedname + suffix
    i = 1
    while new_name in container:
        i += 1
        new_name = unicodedname + '-' + str(i) + suffix

    return new_name


def getSite(resource=None):
    request = get_current_request()
    if resource is not None:
        return find_root(resource)
    elif request is not None:
        return getattr(request, 'root', None)

    return None


def get_obj(oid, only_exists=False):
    root = getSite()
    objectmap = find_objectmap(root)
    obj = objectmap.object_for(oid)
    if only_exists and obj and obj.__parent__ is None:
        return None

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
    query = containers_oids_index.any((root_oid,)) & \
            object_type_index.eq(interface_id)
    return query.execute().all()


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
    query = containers_oids_index.any((root_oid,)) & \
            object_provides_index.any((interface_id,))
    return query.execute().all()


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
    query = container_oid_index.eq(root_oid) & \
            object_type_index.eq(interface_id)
    return query.execute().all()


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
    query = container_oid_index.eq(root_oid) & \
            object_provides_index.any((interface_id,))
    return query.execute().all()


def find_entities(interfaces=None,
                  states=None,
                  all_states_relation=False,
                  not_any=False):
    if interfaces is None:
        interfaces = [IEntity]

    dace_catalog = find_catalog('dace')
    states_index = dace_catalog['object_states']
    object_provides_index = dace_catalog['object_provides']
    query = object_provides_index.any([i.__identifier__ for i in interfaces])
    if states is not None:
        if not_any:
            query = query & states_index.notany(states)
        else:
            if all_states_relation:
                query = query & states_index.all(states)
            else :
                query = query & states_index.any(states)

    entities = query.execute().all()
    return entities


def get_current_process_uid(request):
    action_uid = request.params.get('action_uid', None)
    if action_uid is not None:
        return get_oid(get_obj(int(action_uid)).process)

    return None


def always_false(context, request):
    return False, _('Default validation')


def getBusinessAction(context,
                      request,
                      process_id,
                      node_id,
                      behavior_id=None,
                      action_type=None):
    allactions = []
    context_oid = str(get_oid(context))
    dace_catalog = find_catalog('dace')
    process_id_index = dace_catalog['process_id']
    potential_contexts_ids = dace_catalog['potential_contexts_ids']
    node_id_index = dace_catalog['node_id']
    #behavior_id_index = dace_catalog['behavior_id']
    context_id_index = dace_catalog['context_id']
    object_provides_index = dace_catalog['object_provides']
    query = process_id_index.eq(process_id) & \
            node_id_index.eq(node_id) & \
            object_provides_index.any((IBusinessAction.__identifier__,)) & \
            context_id_index.any(tuple([d.__identifier__ \
                                    for d in context.__provides__.__iro__])) & \
            potential_contexts_ids.any(['any',context_oid])

    if action_type:
        object_type_class_index = dace_catalog['object_type_class']
        query = query & object_type_class_index.eq(action_type.__name__)

    allactions = [action for action in  query.execute().all() \
              if getattr(action, 'validate_mini', always_false)(
                      context, request)[0]]

    def_container = find_service('process_definition_container')
    pd = def_container.get_definition(process_id)
    # Add start workitem
    if not pd.isControlled:
        s_wi = pd.start_process(node_id)[node_id]
        if s_wi:
            swisactions = [action for action in s_wi.actions \
                           if action_type is None or \
                              action._class_.__name__ == action_type.__name__]
            allactions.extend([action for action in swisactions \
                               if action.validate_mini(context, request)[0]])

    if allactions:
        return allactions
    else:
        return None


def getAllSystemActions(request=None,
                        action_type=None):
    if request is None:
        request = get_current_request()

    allactions = []
    dace_catalog = find_catalog('dace')
    issystem_index = dace_catalog['issystem']
    object_provides_index = dace_catalog['object_provides']
    query = object_provides_index.any((IBusinessAction.__identifier__,)) & \
            issystem_index.eq(True)

    allactions = [a for a in query.execute().all()]
    def_container = find_service('process_definition_container')
    allprocess = [(pd.id, pd) for pd in  def_container.definitions \
                  if not pd.isControlled]
    # Add start workitem
    for name, pd in allprocess:
        wis = pd.start_process()
        allactions.extend([action for wi in list(wis.values()) \
                            for action in wi.actions \
                                if action.issystem])
    return allactions


def queryBusinessAction(context,
                        request,
                        process_id,
                        node_id,
                        behavior_id=None,
                        action_type=None):
    return getBusinessAction(context, request,
                        process_id, node_id, behavior_id, IBusinessAction)


def getAllBusinessAction(context,
                         request=None,
                         isautomatic=False,
                         process_id=None,
                         node_id=None,
                         behavior_id=None,
                         process_discriminator=None,
                         action_type=None):
    if request is None:
        request = get_current_request()

    def_container = find_service('process_definition_container')
    context_oid = str(get_oid(context))
    allactions = []
    allprocessdef = []
    dace_catalog = find_catalog('dace')
    context_id_index = dace_catalog['context_id']
    potential_contexts_ids = dace_catalog['potential_contexts_ids']
    object_provides_index = dace_catalog['object_provides']
    query = object_provides_index.any((IBusinessAction.__identifier__,)) & \
            context_id_index.any(tuple([d.__identifier__ \
                                   for d in context.__provides__.__iro__])) & \
            potential_contexts_ids.any(['any', context_oid])

    if action_type:
        object_type_class_index = dace_catalog['object_type_class']
        query = query & object_type_class_index.eq(action_type.__name__)

    if isautomatic:
        isautomatic_index = dace_catalog['isautomatic']
        query = query & isautomatic_index.eq(True)

    if process_id:
        process_id_index = dace_catalog['process_id']
        query = query & process_id_index.eq(process_id)
        pd = def_container.get_definition(process_id)
        allprocessdef = [(process_id, pd)]
    else:
        if process_discriminator:
            allprocessdef = [(pd.id, pd) for pd in def_container.definitions \
                             if pd.discriminator == process_discriminator and \
                                not pd.isControlled]
        else:
            allprocessdef = [(pd.id, pd) for pd in def_container.definitions \
                             if not pd.isControlled]

    if node_id:
        node_id_index = dace_catalog['node_id']
        query = query & node_id_index.eq(node_id)

    if process_discriminator:
        process_discriminator_index = dace_catalog['process_discriminator']
        query = query & process_discriminator_index.eq(process_discriminator)

    allactions = [action for action in  query.execute().all() \
                  if getattr(action, 'validate_mini', always_false)(
                            context, request)[0]]
    # Add start workitem
    for name, pd in allprocessdef:
        wis = [wi for wi in list(pd.start_process(node_id).values()) if wi]
        for wi in wis:
            swisactions = [action for action in wi.actions \
                           if (not isautomatic or \
                               (isautomatic and action.isautomatic)) and \
                              (action_type is None or \
                               action._class_.__name__ == action_type.__name__)]

            allactions.extend([action for action in swisactions \
                               if action.validate_mini(context, request)[0]])

    return allactions


def getWorkItem(context, request, process_id, node_id):
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

    query =  process_id_index.eq(process_id) & \
            node_id_index.eq(process_id+'.'+node_id) & \
            object_provides_index.any((IWorkItem.__identifier__,))
    if process_ids:
        query = query & process_inst_uid_index.any(process_ids)

    results = [w for w in query.execute().all() if w.validate()]
    if results:
        return results[0]

    # Not found in catalog, we return a start workitem
    if not pd.isControlled:
        wi = pd.start_process(node_id)[node_id]
        if wi:
            return wi

    raise Forbidden


def queryWorkItem(context, request, process_id, node_id):
    try:
        wi = getWorkItem(context, request,
            process_id, node_id)
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
            scanner.config.registry.registerAdapter(factory=ob,
                                                    required=(self.context,),
                                                    provided=mprovided,
                                                    name=self.name)

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

            scanner.config.registry.registerUtility(
                                        component, provides, self.name)

        venusian.attach(wrapped, callback)
        return wrapped



_marker = object()
OMIT_ATTRIBUTES = ('data', 'dynamic_properties_def')
#'created_at', 'modified_at'


def copy(obj, container, new_name=None, shared_properties=False,
        composite_properties=False, roles=False,
        omit=OMIT_ATTRIBUTES, select=None):
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
    if omit is not OMIT_ATTRIBUTES:
        omit = set(omit) | set(OMIT_ATTRIBUTES)

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
        container.addtoproperty(propertyname, new)
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
            if descriptor_id in omit:
                continue

            if select is not None and descriptor_id not in select:
                continue

            if isinstance(descriptor, Descriptor):
                value = descriptor.__get__(obj)
                if not value:
                    continue

#                if isinstance(descriptor, (SharedUniqueProperty, SharedMultipleProperty)) and shared_properties:
#                    descriptor.__set__(new, value)  # this can have the side effect of moving value to a different container!
                # TODO do we really want to copy shared properties?
                if isinstance(descriptor, (CompositeUniqueProperty, CompositeMultipleProperty)) and composite_properties:
                    if isinstance(descriptor, CompositeUniqueProperty):
                        value = [value]

                    for item in value:
                        copy(item, (new, descriptor_id), new_name=item.__name__,
                            shared_properties=shared_properties,
                            composite_properties=composite_properties,
                            roles=roles,
                            omit=omit, select=select)

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
    user = get_user_by_login(login, request)
    request.user = user
    callback()
    manager.pop()


def _get_user_by_attr(attr, login, request=None):
    if request is None:
        request = get_current_request()

    registry = request.registry
    app = request.root
    locator = registry.queryMultiAdapter((app, request),
                                         IUserLocator)
    if locator is None:
        locator = DefaultUserLocator(app, request)

    user = getattr(locator, attr)(login)
    return user


def get_user_by_login(login, request=None):
    return _get_user_by_attr('get_user_by_login', login, request)


def get_user_by_userid(login, request=None):
    return _get_user_by_attr('get_user_by_userid', login, request)


def get_userid_by_login(login, request=None):
    user = get_user_by_login(login, request)
    return get_oid(user)


_ctx = None
_socket = None


def get_zmq_context():
    global _ctx
    if _ctx is None:
        _ctx = zmq.Context()

    return _ctx


def get_socket_url():
    return 'tcp://127.0.0.1:12345'


def get_socket():
    global _socket
    if _socket is None:
        ctx = get_zmq_context()
        _socket = ctx.socket(zmq.PUSH)
        _socket.setsockopt(zmq.LINGER, 0)
        _socket.connect(get_socket_url())

    return _socket


class DelayedCallback(object):
    """Schedule the given callback to be called once.

    The callback is called once, after callback_time milliseconds.

    `start` must be called after the DelayedCallback is created.

    The timeout is calculated from when `start` is called.
    """
    def __init__(self, callback, callback_time, identifier=None):
        self.callback = callback
        self.callback_time = callback_time
        self.identifier = identifier
        self._timeout = None

    def start(self):
        s = get_socket()
        s.send_pyobj(('start_in_ioloop', self))

    def start_in_ioloop(self):
        """Start the timer."""
        ioloop = IOLoop.current()
        self._timeout = ioloop.add_timeout(
            ioloop.time() + self.callback_time / 1000.0, self.callback)

    def stop(self):
        """Stop the timer."""
        if self._timeout is not None:
            ioloop = IOLoop.current()
            ioloop.remove_timeout(self._timeout)
            self._timeout = None


def push_callback_after_commit(callback, deadline, identifier=None, **kwargs):
    # Create job object now before the end of the interaction so we have
    # the logged in user.
    job = Job(callback, 'system')
    def after_commit_hook(status, *args, **kws):
        # status is true if the commit succeeded, or false if the commit aborted.
        if status:
            # Set callable now, we are sure to have p_oid
            job.kwargs = kwargs
            dc = DelayedCallback(job, deadline, identifier)
            dc.start()

    transaction.get().addAfterCommitHook(
        after_commit_hook,
        args=(deadline, job))
