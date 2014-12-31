# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi
from dace.testing import FunctionalTests
from .example.objects import Object1, Object2, ObjectShared


class TestProperties(FunctionalTests):

    def test_composition_unique_opposite_shared_unique(self):
        self.app['object1'] = Object1()
        self.app['object2'] = Object2()
        self.app['object3'] = Object1()
        self.app['object4'] = Object2()

        object1 = self.app['object1']
        object2 = self.app['object2']
        object3 = self.app['object3']
        object4 = self.app['object4']

        # Step 1
        # set object2 as composite unique for object1
        object1.setproperty('composition_u', object2)
        self.assertTrue(isinstance(object1.composition_u, Object2))
        self.assertIs(object1.getproperty('composition_u'), object2)
        self.assertIs(object1.composition_u, object2)

        self.assertTrue(isinstance(object2.getproperty('shared2_u'), Object1))
        self.assertIs(object2.getproperty('shared2_u'), object1)

        # Step 2
        # set the other side of the relation
        object2.setproperty('shared2_u', object3)
        self.assertTrue(isinstance(object2.getproperty('shared2_u'), Object1))
        self.assertIs(object2.getproperty('shared2_u'), object3)

        # this should set the relation between object3 and object2
        self.assertTrue(isinstance(object3.getproperty('composition_u'), Object2))
        self.assertIs(object3.getproperty('composition_u'), object2)

        # and set to None the original composition unique relation on object1
        self.assertIs(object1.getproperty('composition_u'), None)

        # Step 3
        object3.setproperty('composition_u', object4)

        self.assertTrue(isinstance(object3.getproperty('composition_u'), Object2))
        self.assertIs(object3.getproperty('composition_u'), object4)

        self.assertTrue(isinstance(object4.getproperty('shared2_u'), Object1))
        self.assertIs(object4.getproperty('shared2_u'), object3)

        self.assertIs(object2.getproperty('shared2_u'), None)
        self.assertIs(object2.__parent__, None)

    def test_composition_multiple_opposite_shared_unique(self):
        self.app['object1'] = Object1()
        self.app['object2'] = Object2()
        self.app['object3'] = Object2()
        self.app['object4'] = Object1()

        object1 = self.app['object1']
        object2 = self.app['object2']
        object3 = self.app['object3']
        object4 = self.app['object4']

        object1.addtoproperty('composition_m', object2)
        self.assertEqual(len(object1.getproperty('composition_m')), 1)
        self.assertIs(object1.getproperty('composition_m')[0], object2)

        self.assertTrue(isinstance(object2.getproperty('shared21_u'), Object1))
        self.assertIs(object2.getproperty('shared21_u'), object1)

        object1.addtoproperty('composition_m', object3)

        self.assertEqual(len(object1.getproperty('composition_m')), 2)
        self.assertIn(object3, object1.getproperty('composition_m'))

        self.assertTrue(isinstance(object3.getproperty('shared21_u'), Object1))
        self.assertIs(object3.getproperty('shared21_u'), object1)

        object2.setproperty('shared21_u', object4)

        self.assertEqual(len(object4.getproperty('composition_m')), 1)
        self.assertIs(object4.getproperty('composition_m')[0], object2)

        self.assertEqual(len(object1.getproperty('composition_m')), 1)
        self.assertIs(object1.getproperty('composition_m')[0], object3)

        self.assertTrue(isinstance(object2.getproperty('shared21_u'), Object1))
        self.assertIs(object2.getproperty('shared21_u'), object4)

    def test_shared_unique_opposite_shared_unique(self):
        self.app['object1'] = Object1()
        self.app['object2'] = Object2()
        self.app['object3'] = Object2()

        object1 = self.app['object1']
        object2 = self.app['object2']
        object3 = self.app['object3']

        object1.setproperty('shared_u', object2)

        self.assertIs(object1.getproperty('shared_u'), object2)
        self.assertIs(object2.getproperty('shared22_u'), object1)

        object1.setproperty('shared_u', object3)

        self.assertIs(object1.getproperty('shared_u'), object3)
        self.assertIs(object3.getproperty('shared22_u'), object1)
        self.assertIs(object2.getproperty('shared22_u'), None)

    def test_shared_multiple_opposite_shared_unique(self):
        self.app['object1'] = Object1()
        self.app['object2'] = Object2()
        self.app['object3'] = Object2()
        self.app['object4'] = Object1()

        object1 = self.app['object1']
        object2 = self.app['object2']
        object3 = self.app['object3']
        object4 = self.app['object4']

        object1.addtoproperty('shared_m', object2)

        self.assertEqual(len(object1.getproperty('shared_m')), 1)
        self.assertIs(object1.getproperty('shared_m')[0], object2)

        self.assertTrue(isinstance(object2.getproperty('shared23_u'), Object1))
        self.assertIs(object2.getproperty('shared23_u'), object1)

        object1.addtoproperty('shared_m', object3)

        self.assertEqual(len(object1.getproperty('shared_m')), 2)
        self.assertIn(object3, object1.getproperty('shared_m'))

        self.assertTrue(isinstance(object3.getproperty('shared23_u'), Object1))
        self.assertIs(object3.getproperty('shared23_u'), object1)

        object2.setproperty('shared23_u', object4)

        self.assertEqual(len(object4.getproperty('shared_m')), 1)
        self.assertIs(object4.getproperty('shared_m')[0], object2)

        self.assertEqual(len(object1.getproperty('shared_m')), 1)
        self.assertIs(object1.getproperty('shared_m')[0], object3)

        self.assertTrue(isinstance(object2.getproperty('shared23_u'), Object1))
        self.assertIs(object2.getproperty('shared23_u'), object4)

    def _create_objects(self):
        from dace.objectofcollaboration.object import Object
        self.app['container'] = container = Object()
        container['folder'] = folder = Object1()
        container['item'] = item = Object2()
        return container, folder, item

    def test_copy_composite_unique_and_role(self):
        container, folder, item = self._create_objects()
        system = self.app['principals']['users']['system']
        from dace.objectofcollaboration.principal.util import (
                grant_roles, get_roles)
        grant_roles(system, (('System', folder),))
        roles = get_roles(user=system, obj=folder)
        self.assertEqual(roles, ['System'])

        folder.composition_u = item

        from dace.util import copy
        foldercopy = copy(folder, container)
        self.assertIs(folder.composition_u, item)
        self.assertIs(item.shared2_u, folder)
        self.assertIs(foldercopy.composition_u, None)
        self.assertTrue(hasattr(foldercopy, '__oid__'))
        self.assertEqual(foldercopy.__name__, 'copy_of_folder')
        # verify roles weren't copied
        roles = get_roles(user=system, obj=foldercopy)
        self.assertEqual(roles, [])

        foldercopy2 = copy(folder, container, composite_properties=True,
                roles=True)
        self.assertEqual(foldercopy2.__name__, 'copy_of_folder-2')
        # no change for folder and item
        self.assertIs(folder.composition_u, item)
        self.assertIs(item.shared2_u, folder)
        # the copy foldercopy2 of folder contains a copy of item
        # which is item2 here
        self.assertIsNot(foldercopy2.composition_u, None)
        item2 = foldercopy2.composition_u
        self.assertIsNot(item, item2)
        # item2 has the same name of item
        self.assertEqual(item2.__name__, 'item')
        self.assertTrue(hasattr(item2, '__oid__'))
        # and the copied composition item2 point to foldercopy2
        self.assertIs(item2.shared2_u, foldercopy2)

        # roles should be copied
        roles = get_roles(user=system, obj=foldercopy2)
        self.assertEqual(roles, ['System'])

    def test_dont_copy_composite_multiple(self):
        container, folder, item = self._create_objects()
        folder.addtoproperty('composition_m', item)

        from dace.util import copy
        foldercopy = copy(folder, container)
        # no change for folder and item
        self.assertEqual(folder.composition_m, [item])
        self.assertIs(item.shared21_u, folder)
        # new foldercopy is empty
        self.assertEqual(len(foldercopy.composition_m), 0)
        # The copy has been indexed in objectmap
        self.assertTrue(hasattr(foldercopy, '__oid__'))
        self.assertEqual(foldercopy.__name__, 'copy_of_folder')

    def test_copy_composite_multiple(self):
        container, folder, item = self._create_objects()
        folder.addtoproperty('composition_m', item)

        from dace.util import copy
        foldercopy = copy(folder, container, composite_properties=True)
        self.assertEqual(foldercopy.__name__, 'copy_of_folder')
        # no change for folder and item
        self.assertEqual(folder.composition_m, [item])
        self.assertIs(item.shared21_u, folder)
        # the copy foldercopy of folder contains a copy of item
        # which is item2 here
        self.assertEqual(len(foldercopy.composition_m), 1)
        item2 = foldercopy.composition_m[0]
        self.assertIsNot(item, item2)
        # item2 has the same name of item
        self.assertEqual(item2.__name__, 'item')
        self.assertTrue(hasattr(item2, '__oid__'))
        # and the copied composition item2 point to foldercopy
        self.assertIs(item2.shared21_u, foldercopy)

    def test_copy_composite_relations(self):
        container, folder, item = self._create_objects()
        folder.addtoproperty('composition_m', item)
        container['item2'] = item2 = Object2()
        folder.composition_u = item2

        from dace.util import copy
        foldercopy = copy(folder, container, composite_properties=True)
        self.assertEqual(len(foldercopy.composition_m), 1)
        self.assertIsNot(foldercopy.composition_u, None)

    def test_copy_composite_relations_but_omit_composite_u(self):
        container, folder, item = self._create_objects()
        folder.addtoproperty('composition_m', item)
        container['item2'] = item2 = Object2()
        folder.composition_u = item2

        from dace.util import copy
        foldercopy = copy(folder, container, composite_properties=True,
                          omit=('composition_u',))
        self.assertEqual(len(foldercopy.composition_m), 1)
        self.assertIs(foldercopy.composition_u, None)

    def test_copy_composite_relations_select_composition_m(self):
        container, folder, item = self._create_objects()
        folder.addtoproperty('composition_m', item)
        container['item2'] = item2 = Object2()
        folder.composition_u = item2

        from dace.util import copy
        foldercopy = copy(folder, container, composite_properties=True,
                          select=('composition_m',))
        self.assertEqual(len(foldercopy.composition_m), 1)
        self.assertIs(foldercopy.composition_u, None)

    def test_copy_composite_relations_select_and_omit_composition_m(self):
        container, folder, item = self._create_objects()
        folder.addtoproperty('composition_m', item)
        container['item2'] = item2 = Object2()
        folder.composition_u = item2

        from dace.util import copy
        foldercopy = copy(folder, container, composite_properties=True,
                          omit=('composition_m',), select=('composition_m',))
        # omit overrides select
        self.assertEqual(len(foldercopy.composition_m), 0)
        self.assertIs(foldercopy.composition_u, None)

    def test_rename_composite_multiple(self):
        self.app['object1'] = Object1()
        self.app['object2'] = Object2()
        self.app['object3'] = Object2()

        object1 = self.app['object1']
        object2 = self.app['object2']
        object3 = self.app['object3']

        object1.addtoproperty('composition_m', object2)
        object1.addtoproperty('composition_m', object3)
        self.assertEqual(len(object1.getproperty('composition_m')), 2)
        self.assertIn(object2, object1.getproperty('composition_m'))
        self.assertIn(object3, object1.getproperty('composition_m'))
        self.assertEqual(object2.__name__, 'object2')
        self.assertTrue('object2' in object1.data)
        self.assertFalse('newname_object2' in object1.data)

        object1.rename('object2', 'newname_object2')
        self.assertEqual(len(object1.getproperty('composition_m')), 2)
        self.assertIn(object2, object1.getproperty('composition_m'))
        self.assertIn(object3, object1.getproperty('composition_m'))
        self.assertEqual(object2.__name__, 'newname_object2')
        self.assertTrue('newname_object2' in object1.data)
        self.assertFalse('object2' in object1.data)

    def test_rename_composite_unique(self):
        self.app['object1'] = Object1()
        self.app['object2'] = Object2()

        object1 = self.app['object1']
        object2 = self.app['object2']

        object1.setproperty('composition_u', object2)
        self.assertIs(object2, object1.getproperty('composition_u'))
        self.assertEqual(object2.__name__, 'object2')
        self.assertTrue('object2' in object1.data)
        self.assertFalse('newname_object2' in object1.data)

        object1.rename('object2', 'newname_object2')
        self.assertIs(object2, object1.getproperty('composition_u'))
        self.assertEqual(object2.__name__, 'newname_object2')
        self.assertTrue('newname_object2' in object1.data)
        self.assertFalse('object2' in object1.data)


    def test_move_composite_unique(self):
        self.app['object1'] = Object1()
        self.app['object2'] = Object1()
        self.app['object3'] = Object2()

        object1 = self.app['object1']
        object2 = self.app['object2']
        object3 = self.app['object3']

        object1.setproperty('composition_u', object3)
        self.assertIs(object3, object1.getproperty('composition_u'))
        self.assertEqual(object3.__name__, 'object3')
        self.assertTrue('object3' in object1.data)
        self.assertIs(None, object2.getproperty('composition_u'))

        object1.move('object3', (object2, 'composition_u'), 'newname_object3')
        self.assertIs(object3, object2.getproperty('composition_u'))
        self.assertEqual(object3.__name__, 'newname_object3')
        self.assertTrue('newname_object3' in object2.data)
        self.assertIs(None, object1.getproperty('composition_u'))


    def test_move_composite_multiple(self):
        self.app['object1'] = Object1()
        self.app['object2'] = Object1()
        self.app['object3'] = Object2()
        self.app['object4'] = Object2()

        object1 = self.app['object1']
        object2 = self.app['object2']
        object3 = self.app['object3']
        object4 = self.app['object4']

        object1.addtoproperty('composition_m', object3)
        object1.addtoproperty('composition_m', object4)
        self.assertEqual(len(object1.getproperty('composition_m')), 2)
        self.assertIn(object4, object1.getproperty('composition_m'))
        self.assertIn(object3, object1.getproperty('composition_m'))
        self.assertEqual(object4.__name__, 'object4')
        self.assertTrue('object4' in object1.data)
        self.assertEqual(len(object2.getproperty('composition_m')), 0)

        object1.move('object4', (object2, 'composition_m'), 'newname_object4')
        self.assertEqual(len(object1.getproperty('composition_m')), 1)
        self.assertIn(object3, object1.getproperty('composition_m'))
        self.assertEqual(len(object2.getproperty('composition_m')), 1)
        self.assertIn(object4, object2.getproperty('composition_m'))
        self.assertEqual(object4.__name__, 'newname_object4')
        self.assertTrue('newname_object4' in object2.data)

    def test_composition_multiple_opposite_shared_remove(self):
        self.app['object1'] = Object1()
        self.app['object2'] = Object2()
        self.app['object3'] = ObjectShared()

        object1 = self.app['object1']
        object2 = self.app['object2']
        object3 = self.app['object3']

        object1.addtoproperty('composition_m', object2)
        self.assertEqual(len(object1.getproperty('composition_m')), 1)
        self.assertIs(object1.getproperty('composition_m')[0], object2)

        self.assertTrue(isinstance(object2.getproperty('shared21_u'), Object1))
        self.assertIs(object2.getproperty('shared21_u'), object1)

        object1.addtoproperty('composition_m', object3)

        self.assertEqual(len(object1.getproperty('composition_m')), 2)
        self.assertIn(object3, object1.getproperty('composition_m'))

        object3.setproperty('shared', object2)
        object3.addtoproperty('shared_m', object2)
        self.assertIs(object3.getproperty('shared'), object2)
        self.assertEqual(len(object3.getproperty('shared_m')), 1)
        self.assertIn(object2, object3.getproperty('shared_m'))

        object1.delfromproperty('composition_m', object2)
        self.assertIs(object3.getproperty('shared'), None)
        self.assertEqual(len(object3.getproperty('shared_m')), 0)


    def test_set_get_data(self):
        self.app['object1'] = Object1()
        object1 = self.app['object1']
        class Node:
            pass

        namenode = Node()
        namenode.name = 'name'
        compu_node = Node()
        compu_node.name = 'composition_u'
        schema = [namenode, compu_node]
        self.assertEqual(hasattr(object1, 'name'), False)
        object1.set_data({'name': 'object1_name'})
        self.assertEqual(hasattr(object1, 'name'), True)
        self.assertEqual(object1.name, 'object1_name')

        data = object1.get_data(schema)
        self.assertIn('name', data)
        self.assertEqual(data['name'], 'object1_name')
        self.assertIn('composition_u', data)
        self.assertEqual(data['composition_u'], None)

        self.app['object2'] = Object1()
        object2 = self.app['object2']
        object1.set_data({'composition_u': object2})

        data = object1.get_data(schema)
        self.assertIn('composition_u', data)
        self.assertEqual(data['composition_u'], object2)





