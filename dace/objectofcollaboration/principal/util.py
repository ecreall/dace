# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi

import datetime
import random

from pyramid.threadlocal import get_current_request

from substanced.util import get_oid, find_service
from substanced.principal import User

from dace.relations import connect, disconnect, find_relations
from dace.objectofcollaboration.principal import Group
from dace.util import getSite
from .role import DACE_ROLES, Anonymous as RoleAnonymous


try:
    basestring
except NameError:
    basestring = str


_marker = object()


class Anonymous(object):
    __name__ = 'Anonymous'
    name = 'Anonymous'
    locale = 'fr'
    __oid__ = 20159291037391313


def anonymous_oid_generator():
    date_tuple = datetime.datetime.timetuple(datetime.datetime.today())
    descriminator = random.choice(range(100))
    oid = int(''.join([str(element) for element in date_tuple if element >= 0]))
    return oid+descriminator


def get_current(request=None):
    if request is None:
        request = get_current_request()

    result = request.user
    if result is None:
        result = Anonymous()
#        result.__oid__ = anonymous_oid_generator()

    return result


def get_roles(user=None, obj=None,
              root=None, ignore_groups=False):
    if user is None:
        user = get_current()

    if isinstance(user, Anonymous):
        return [RoleAnonymous.name]

    if root is None:
        root = getSite()

    if obj is None:
        obj = root

    opts = {u'source_id': get_oid(user),
            u'target_id': get_oid(obj)}
    opts[u'reftype'] = 'Role'
    roles = [r.relation_id for r in find_relations(obj, opts).all()]
    principals = find_service(root, 'principals')
    sd_admin = principals['users']['admin']
    if sd_admin is user and 'Admin' not in roles:
        roles.append('Admin')

    groups = []
    if not ignore_groups:
        groups.extend(getattr(user, 'groups', []))

    for group in groups:
        roles.extend(get_roles(group, obj, root))

    return list(set(roles))


def grant_roles(user=None, roles=(), root=None):
    if not roles:
        return

    if user is None:
        user = get_current()

    if isinstance(user, Anonymous):
        return

    normalized_roles = []
    if root is None:
        root = getSite()

    for role in roles:
        if isinstance(role, basestring):
            normalized_roles.append((role, root))
        else:
            normalized_roles.append(role)

    for role in normalized_roles:
        if role[0] in DACE_ROLES:
            obj = role[1]
            opts = {}
            opts[u'relation_id'] = role[0]
            opts[u'reftype'] = 'Role'
            if not has_any_roles(user, (role,), True, root=root):
                connect(user, obj, **opts)
                if obj is not root:
                    connect(user, root, **opts)

    if hasattr(user, 'reindex'):
        user.reindex()


def revoke_roles(user=None, roles=(), root=None):
    if not roles:
        return

    if user is None:
        user = get_current()

    if isinstance(user, Anonymous):
        return #TODO use cookies to revoke roles

    normalized_roles = []
    if root is None:
        root = getSite()

    for role in roles:
        if isinstance(role, basestring):
            normalized_roles.append((role, root))
        else:
            normalized_roles.append(role)

    for role in normalized_roles:
        obj = role[1]
        opts = {u'source_id': get_oid(user),
                u'target_id': get_oid(obj)}
        opts[u'relation_id'] = role[0]
        opts[u'reftype'] = 'Role'
        relations = [r for r in find_relations(obj, opts).all()]
        if not(obj is root):
            opts[u'target_id'] = get_oid(root)
            relations.extend([r for r in find_relations(obj, opts).all()])

        for relation in relations:
            disconnect(relation)

    if hasattr(user, 'reindex'):
        user.reindex()


def _get_allsuperiors(role_id, root):
    return [(r.name, root) for r in getattr(DACE_ROLES.get(role_id, _marker),
                                            'all_superiors', [])]


def has_role(role, user=None, ignore_superiors=False, root=None):
    if root is None:
        root = getSite()

    if user is None:
        user = get_current()

    normalized_roles = {}
    if len(role) == 1:
        role = (role[0], root)

    normalized_roles[role[0]] = role[1]
    if not ignore_superiors:
        normalized_roles.update(dict(_get_allsuperiors(role[0], root)))

    if isinstance(user, Anonymous):
        return RoleAnonymous.name in normalized_roles
        #TODO use cookies to find roles

    if 'Admin' in  normalized_roles:
        principals = find_service(root, 'principals')
        sd_admin = principals['users']['admin']
        if sd_admin is user:
            return True

    groups = list(getattr(user, 'groups', []))
    groups.append(user)
    for role in normalized_roles:
        context = normalized_roles[role]
        opts = {u'source_id': (
                    'any', tuple(sorted([get_oid(g) for g in groups]))),
                u'target_id': get_oid(context)}
        opts[u'relation_id'] = role
        opts[u'reftype'] = 'Role'
        if find_relations(root, opts):
            return True

    return False


def has_any_roles(user=None,
                  roles=(),
                  ignore_superiors=False,
                  root=None):
    if not roles:
        return True

    normalized_roles = {}
    if root is None:
        root = getSite()

    for role in roles:
        if isinstance(role, basestring):
            normalized_roles[role] = root
            if not ignore_superiors:
                normalized_roles.update(dict(_get_allsuperiors(role, root)))
        else:
            normalized_roles[role[0]] = role[1]
            if not ignore_superiors:
                normalized_roles.update(dict(_get_allsuperiors(role[0], root)))

    if user is None:
        user = get_current()

    if isinstance(user, Anonymous):
        return RoleAnonymous.name in normalized_roles

    if 'Admin' in  normalized_roles:
        principals = find_service(root, 'principals')
        sd_admin = principals['users']['admin']
        if sd_admin is user:
            return True

    groups = list(getattr(user, 'groups', []))
    groups.append(user)
    for role in normalized_roles:
        context = normalized_roles[role]
        opts = {u'source_id': (
                    'any', tuple(sorted([get_oid(g) for g in groups]))),
                u'target_id': get_oid(context)}
        opts[u'relation_id'] = role
        opts[u'reftype'] = 'Role'
        if find_relations(root, opts):
            return True

    return False


def has_all_roles(user=None, 
                  roles=(), 
                  ignore_superiors=False, 
                  root=None):
    if not roles:
        return True

    normalized_roles = {}
    if root is None:
        root = getSite()

    for role in roles:
        if isinstance(role, basestring):
            normalized_roles[role] = root
        else:
            normalized_roles[role[0]] = role[1]

    if user is None:
        user = get_current()

    if isinstance(user, Anonymous):
        return False 
        #TODO use cookies to find roles

    for role in normalized_roles:
        if not has_any_roles(user, (role, ), ignore_superiors, root):
            return False

    return True


def get_users_with_role(role=None, root=None):
    if role is None:
        return []

    if root is None:
        root = getSite()

    normalized_role = role
    if isinstance(role, basestring):
        normalized_role = (role, root)

    opts = {u'target_id': get_oid(normalized_role[1])}
    opts[u'relation_id'] = normalized_role[0]
    opts[u'reftype'] = 'Role'
    users = list(set([r.source for r in find_relations(normalized_role[1], opts).all()]))
    result = [u for u in users if isinstance(u, User)]
    groups = [g.members for g in users if isinstance(g, Group)]
    groups = [item for sublist in groups for item in sublist]
    result.extend(groups)
    return list(set(result))


def get_objects_with_role(user=None, role=None, root=None):
    if role is None:
        return []

    if user is None:
        user = get_current()

    if isinstance(user, Anonymous):
        return False 
        #TODO use cookies to find objects

    if root is None:
        root = getSite()

    opts = {u'source_id': get_oid(user)}
    opts[u'relation_id'] = role
    opts[u'reftype'] = 'Role'
    objects = [r.target for r in find_relations(root, opts).all()]
    objects = list(set(objects))
    if root in objects:
        objects.remove(root)

    return objects


def get_access_keys(user, root=None, to_exclude=[]):
    if isinstance(user, Anonymous):
        return ['anonymous']

    principals = find_service(user, 'principals')
    sd_admin = principals['users']['admin']
    pricipal_root = getSite()
    if root is None:
        root = pricipal_root

    root_oid = get_oid(root)
    principal_root_oid = get_oid(pricipal_root)
    if sd_admin is user:
        return list(set([('admin'+'_'+str(root_oid)).lower(),
                ('admin'+'_'+str(principal_root_oid)).lower()]))

    groups = list(getattr(user, 'groups', []))
    groups.append(user)
    relations = []
    for group in groups:
        opts = {u'source_id': get_oid(group)}
        opts[u'reftype'] = 'Role'
        relations.extend(list(find_relations(group, opts).all()))

    result = [(t.relation_id+'_'+str(t.target_id)).lower() \
              for t in relations if t.target_id not in to_exclude]
    for relation in relations:
        if relation.relation_id == 'Admin':
            result.append(('admin'+'_'+str(principal_root_oid)).lower())
            break

    return list(set(result))
