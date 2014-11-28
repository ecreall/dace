# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi
from dace.testing import FunctionalTests

from dace.objectofcollaboration.principal.util import (
    grant_roles,
    get_roles,
    revoke_roles,
    has_any_roles,
    has_all_roles,
    get_users_with_role,
    get_objects_with_role)
from .example.objects import Object1, Object2


class TestRoleManagment(FunctionalTests):

    def _create_objects(self):
        self.app['object1'] = Object1()
        self.app['object2'] = Object2()

        object1 = self.app['object1']
        object2 = self.app['object2']
        return object1, object2

    def test_grantroles(self):
        object1, object2 = self._create_objects()
        user = self.request.user #Admin
        self.assertEqual(len(get_roles(user)), 1)
        self.assertTrue(has_any_roles(user, roles=('Admin', )))
        grant_roles(user, roles=('Collaborator', ('Owner', object1)))
        self.assertTrue(has_any_roles(user, roles=('Collaborator', 'Owner')))
        self.assertTrue(has_any_roles(user, roles=('Collaborator', ('Owner', object1))))
        self.assertFalse(has_any_roles(user, roles=(('Owner', object2),)))

        roles = get_roles(user)
        self.assertEqual(len(roles), 3)
        self.assertIn('Collaborator',roles)
        self.assertIn('Owner',roles)
        self.assertIn('Admin',roles)

        self.assertTrue(has_all_roles(user, ('Collaborator', 'Owner')))
        self.assertFalse(has_all_roles(user, ('Collaborator', 'Owner', 'Other')))

        users = get_users_with_role(role=('Owner', object1))
        self.assertEqual(len(users), 1)
        self.assertIn(self.request.user,users)

        users = get_users_with_role(role='Owner')
        self.assertEqual(len(users), 1)
        self.assertIn(self.request.user,users)

        objects = get_objects_with_role(user=self.request.user, role='Owner')
        self.assertEqual(len(objects), 1)
        self.assertIn(object1,objects)
        
        revoke_roles(user, roles=(('Owner', object1),))
        self.assertFalse(has_all_roles(user, ('Collaborator', 'Owner')))
        self.assertTrue(has_all_roles(user, ('Collaborator', )))

        revoke_roles(user, roles=('Collaborator', ))
        self.assertEqual(len(get_roles(user)), 1)


        self.request.user = self.users['alice']
        user = self.request.user  #Alice
        roles = get_roles(user)
        self.assertEqual(len(roles), 0)
        grant_roles(user, roles=('Admin',))
        roles = get_roles(user)
        self.assertEqual(len(roles), 1)
        self.assertIn('Admin',roles)
        self.assertTrue(has_any_roles(user, roles=('Collaborator', )))

        revoke_roles(user, roles=('Admin', ))
        self.assertFalse(has_any_roles(user, roles=('Collaborator', )))
        grant_roles(user, roles=('Developer',))
        roles = get_roles(user)
        self.assertEqual(len(roles), 1)
        self.assertIn('Developer',roles)
        self.assertTrue(has_any_roles(user, roles=('Collaborator', )))
        self.assertFalse(has_any_roles(user, ('Collaborator', ), True)) #exclude superiors
 
        #Anonymous
        self.request.user = None
        roles = get_roles()
        self.assertEqual(len(roles), 1)
        self.assertIn('Anonymous',roles)
        self.assertFalse(has_any_roles(roles=('Collaborator', 'Owner')))
        self.assertTrue(has_any_roles(roles=('Anonymous',)))


