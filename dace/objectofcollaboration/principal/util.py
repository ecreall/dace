from pyramid.threadlocal import get_current_request

from substanced.util import get_oid

from dace.relations import connect, disconnect, find_relations
from dace.util import getSite

try:
    basestring
except NameError:
    basestring = str

def get_current():
    request = get_current_request()
    return request.user


def get_roles(user=None, obj=None):
    if user is None:
        user = get_current()

    if user is None:
        return ['Anonymous']

    if obj is None:
        obj = getSite()

    opts = {u'source_id': get_oid(user),#Anonyme ?
            u'target_id': get_oid(obj)} 
    opts[u'reftype'] = 'Role'
    roles = [r.relation_id for r in find_relations(obj, opts).all()]
    return roles


def grant_roles(user=None, roles=()):
    if not roles:
        return

    if user is None:
        user = get_current()

    if user is None:
        return 

    normalized_roles = []
    root = getSite()
    for role in roles:
        if isinstance(role, basestring):
            normalized_roles.append((role, root))
        else:
            normalized_roles.append(role)

    for role in normalized_roles:
        obj = role[1]
        opts = {}
        opts[u'relation_id'] = role[0]
        opts[u'reftype'] = 'Role'
        if not has_any_roles(user, (role,)):
            connect(user, obj, **opts)
            if not(obj is root):
                connect(user, root, **opts)


def revoke_roles(user=None, roles=()):
    if not roles:
        return

    if user is None:
        user = get_current()

    if user is None:
        return 

    normalized_roles = []
    root = getSite()
    for role in roles:
        if isinstance(role, basestring):
            normalized_roles.append((role, root))
        else:
            normalized_roles.append(role)

    for role in normalized_roles:
        obj = role[1]
        opts = {u'source_id': get_oid(user),#Anonyme ?
                u'target_id': get_oid(obj)} 
        opts[u'relation_id'] = role[0]
        opts[u'reftype'] = 'Role'
        relations = [r for r in find_relations(obj, opts).all()]
        if not(obj is root):
            opts[u'target_id'] = get_oid(root) 
            relations.extend([r for r in find_relations(obj, opts).all()])

        for relation in relations:
            disconnect(relation)
   

def has_any_roles(user=None, roles=()):
    if not roles:
        return True

    normalized_roles = []
    for role in roles:
        if isinstance(role, basestring):
            normalized_roles.append((role, getSite()))
        else:
            normalized_roles.append(role)

    if user is None:
        user = get_current()

    if user is None:
        roles_id = [r[0] for r in normalized_roles]
        if 'Anonymous' in roles_id:
            return True

        return False
    
    for role in normalized_roles:
        opts = {u'source_id': get_oid(user),#Anonyme ?
                u'target_id': get_oid(role[1])} 
        opts[u'relation_id'] = role[0]
        opts[u'reftype'] = 'Role'
        role_relations = [r for r in find_relations(role[1], opts).all()]
        if role_relations:
            return True
            
    return False


def has_all_roles(user=None, roles=()):
    if not roles:
        return True

    normalized_roles = []
    for role in roles:
        if isinstance(role, basestring):
            normalized_roles.append((role, getSite()))
        else:
            normalized_roles.append(role)

    if user is None:
        user = get_current()

    if user is None: #TODO Anonymous
        return False

    for role in normalized_roles:
        opts = {u'source_id': get_oid(user),
                u'target_id': get_oid(role[1])} 
        opts[u'relation_id'] = role[0]
        opts[u'reftype'] = 'Role'
        role_relations = [r for r in find_relations(role[1], opts).all()]
        if not role_relations:
            return False
            
    return True


def get_users_with_role(role=None):
    if role is None:
        return []

    normalized_role = role
    if isinstance(role, basestring):
        normalized_role = (role, getSite())

    opts = {u'target_id': get_oid(normalized_role[1])} 
    opts[u'relation_id'] = normalized_role[0]
    opts[u'reftype'] = 'Role'
    users = [r.source for r in find_relations(normalized_role[1], opts).all()]
    return list(set(users))


def get_objects_with_role(user=None, role=None):
    if role is None:
        return []

    if user is None:
        user = get_current()

    if user is None: #TODO Anonymous
        return False

    root = getSite()
    opts = {u'source_id': get_oid(user)} 
    opts[u'relation_id'] = role
    opts[u'reftype'] = 'Role'
    objects = [r.target for r in find_relations(root, opts).all()]
    objects = list(set(objects))
    if not (len(objects) == 1 and objects[0] is root):
        objects.remove(root)

    return objects
