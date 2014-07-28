from dace.testing import FunctionalTests
from .example.objects import Object1, Object2


class TestProperties(FunctionalTests):

    def _create_objects_cu_su(self):
        self.app['object1'] = Object1()
        self.app['object2'] = Object2()
        self.app['object3'] = Object1()
        self.app['object4'] = Object2()

        object1 = self.app['object1']
        object2 = self.app['object2']
        object3 = self.app['object3']
        object4 = self.app['object4']
        return object1, object2, object3, object4

    def test_composition_unique_opposite_shared_unique(self):
        object1, object2, object3, object4 = self._create_objects_cu_su()
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

    def _create_objects_cm_su(self):
        self.app['object1'] = Object1()
        self.app['object2'] = Object2()
        self.app['object3'] = Object2()
        self.app['object4'] = Object1()

        object1 = self.app['object1']
        object2 = self.app['object2']
        object3 = self.app['object3']
        object4 = self.app['object4']
        return object1, object2, object3, object4

    def test_composition_multiple_opposite_shared_unique(self):
        object1, object2, object3, object4 = self._create_objects_cm_su()
        object1.addtoproperty('composition_m', object2)
        self.assertEqual(len(object1.getproperty('composition_m')), 1)
        self.assertIs(object1.getproperty('composition_m')[0], object2)

        self.assertTrue(isinstance(object2.getproperty('shared21_u'), Object1))
        self.assertIs(object2.getproperty('shared21_u'), object1)

        object1.addtoproperty('composition_m', object3)

        self.assertEqual(len(object1.getproperty('composition_m')), 2)
        self.assertTrue((object3 in object1.getproperty('composition_m')))

        self.assertTrue(isinstance(object3.getproperty('shared21_u'), Object1))
        self.assertIs(object3.getproperty('shared21_u'), object1)

        object2.setproperty('shared21_u', object4)

        self.assertEqual(len(object4.getproperty('composition_m')), 1)
        self.assertIs(object4.getproperty('composition_m')[0], object2)

        self.assertEqual(len(object1.getproperty('composition_m')), 1)
        self.assertIs(object1.getproperty('composition_m')[0], object3)

        self.assertTrue(isinstance(object2.getproperty('shared21_u'), Object1))
        self.assertIs(object2.getproperty('shared21_u'), object4)


    def _create_objects_su_su(self):
        self.app['object1'] = Object1()
        self.app['object2'] = Object2()
        self.app['object3'] = Object2()

        object1 = self.app['object1']
        object2 = self.app['object2']
        object3 = self.app['object3']
        return object1, object2, object3

    def test_shared_unique_opposite_shared_unique(self):
        object1, object2, object3 = self._create_objects_su_su()
        object1.setproperty('shared_u', object2)

        self.assertIs(object1.getproperty('shared_u'), object2)
        self.assertIs(object2.getproperty('shared22_u'), object1)

        object1.setproperty('shared_u', object3)

        self.assertIs(object1.getproperty('shared_u'), object3)
        self.assertIs(object3.getproperty('shared22_u'), object1)
        self.assertIs(object2.getproperty('shared22_u'), None)

    def _create_objects_sm_su(self):
        self.app['object1'] = Object1()
        self.app['object2'] = Object2()
        self.app['object3'] = Object2()
        self.app['object4'] = Object1()

        object1 = self.app['object1']
        object2 = self.app['object2']
        object3 = self.app['object3']
        object4 = self.app['object4']
        return object1, object2, object3, object4

    def test_shared_multiple_opposite_shared_unique(self):
        object1, object2, object3, object4 = self._create_objects_sm_su()
        object1.addtoproperty('shared_m', object2)

        self.assertEqual(len(object1.getproperty('shared_m')), 1)
        self.assertIs(object1.getproperty('shared_m')[0], object2)

        self.assertTrue(isinstance(object2.getproperty('shared23_u'), Object1))
        self.assertIs(object2.getproperty('shared23_u'), object1)

        object1.addtoproperty('shared_m', object3)

        self.assertEqual(len(object1.getproperty('shared_m')), 2)
        self.assertTrue((object3 in object1.getproperty('shared_m')))

        self.assertTrue(isinstance(object3.getproperty('shared23_u'), Object1))
        self.assertIs(object3.getproperty('shared23_u'), object1)

        object2.setproperty('shared23_u', object4)

        self.assertEqual(len(object4.getproperty('shared_m')), 1)
        self.assertIs(object4.getproperty('shared_m')[0], object2)

        self.assertEqual(len(object1.getproperty('shared_m')), 1)
        self.assertIs(object1.getproperty('shared_m')[0], object3)

        self.assertTrue(isinstance(object2.getproperty('shared23_u'), Object1))
        self.assertIs(object2.getproperty('shared23_u'), object4)
