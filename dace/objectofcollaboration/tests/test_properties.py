from dace.testing import FunctionalTests
from .example.objects import Object1, Object2


class TestProperties(FunctionalTests):


    def _del_objects(self):
        try:
            self.app.remove('object1')
        except :
            pass

        try:
            self.app.remove('object2')
        except :
            pass

        try:
            self.app.remove('object3')
        except :
            pass

        try:
            self.app.remove('object4')
        except :
            pass

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

    def test_composition_unique_opposite_schared_unique(self):
        object1, object2, object3, object4 = self._create_objects_cu_su()
        object1.setproperty('composition_u', object2)
        self.assertTrue(isinstance(object1.getproperty('composition_u'), Object2))
        self.assertIs(object1.getproperty('composition_u'), object2)

        self.assertTrue(isinstance(object2.getproperty('schared2_u'), Object1))
        self.assertIs(object2.getproperty('schared2_u'), object1)

        object2.setproperty('schared2_u', object3)

        self.assertTrue(isinstance(object3.getproperty('composition_u'), Object2))
        self.assertIs(object3.getproperty('composition_u'), object2)

        self.assertIs(object1.getproperty('composition_u'), None)

        self.assertTrue(isinstance(object2.getproperty('schared2_u'), Object1))
        self.assertIs(object2.getproperty('schared2_u'), object3)

        object3.setproperty('composition_u', object4)

        self.assertTrue(isinstance(object3.getproperty('composition_u'), Object2))
        self.assertIs(object3.getproperty('composition_u'), object4)

        self.assertTrue(isinstance(object4.getproperty('schared2_u'), Object1))
        self.assertIs(object4.getproperty('schared2_u'), object3)

        self.assertIs(object2.getproperty('schared2_u'), None)
        self.assertIs(object2.__parent__, None)
        self._del_objects()

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

    def test_composition_multiple_opposite_schared_unique(self):
        object1, object2, object3, object4 = self._create_objects_cm_su()
        object1.addtoproperty('composition_m', object2)
        self.assertEqual(len(object1.getproperty('composition_m')), 1)
        self.assertIs(object1.getproperty('composition_m')[0], object2)

        self.assertTrue(isinstance(object2.getproperty('schared21_u'), Object1))
        self.assertIs(object2.getproperty('schared21_u'), object1)

        object1.addtoproperty('composition_m', object3)

        self.assertEqual(len(object1.getproperty('composition_m')), 2)
        self.assertTrue((object3 in object1.getproperty('composition_m')))

        self.assertTrue(isinstance(object3.getproperty('schared21_u'), Object1))
        self.assertIs(object3.getproperty('schared21_u'), object1)

        object2.setproperty('schared21_u', object4)

        self.assertEqual(len(object4.getproperty('composition_m')), 1)
        self.assertIs(object4.getproperty('composition_m')[0], object2)

        self.assertEqual(len(object1.getproperty('composition_m')), 1)
        self.assertIs(object1.getproperty('composition_m')[0], object3)

        self.assertTrue(isinstance(object2.getproperty('schared21_u'), Object1))
        self.assertIs(object2.getproperty('schared21_u'), object4)
        self._del_objects()


    def _create_objects_su_su(self):
        self.app['object1'] = Object1()
        self.app['object2'] = Object2()
        self.app['object3'] = Object2()

        object1 = self.app['object1']
        object2 = self.app['object2']
        object3 = self.app['object3']
        return object1, object2, object3


    def test_schared_unique_opposite_schared_unique(self):
        object1, object2, object3 = self._create_objects_su_su()
        object1.setproperty('schared_u', object2)

        self.assertIs(object1.getproperty('schared_u'), object2)
        self.assertIs(object2.getproperty('schared22_u'), object1)

        object1.setproperty('schared_u', object3)

        self.assertIs(object1.getproperty('schared_u'), object3)
        self.assertIs(object3.getproperty('schared22_u'), object1)
        self.assertIs(object2.getproperty('schared22_u'), None)
        self._del_objects()


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

    def test_schared_multiple_opposite_schared_unique(self):
        object1, object2, object3, object4 = self._create_objects_sm_su()
        object1.addtoproperty('schared_m', object2)

        self.assertEqual(len(object1.getproperty('schared_m')), 1)
        self.assertIs(object1.getproperty('schared_m')[0], object2)

        self.assertTrue(isinstance(object2.getproperty('schared23_u'), Object1))
        self.assertIs(object2.getproperty('schared23_u'), object1)

        object1.addtoproperty('schared_m', object3)

        self.assertEqual(len(object1.getproperty('schared_m')), 2)
        self.assertTrue((object3 in object1.getproperty('schared_m')))

        self.assertTrue(isinstance(object3.getproperty('schared23_u'), Object1))
        self.assertIs(object3.getproperty('schared23_u'), object1)

        object2.setproperty('schared23_u', object4)

        self.assertEqual(len(object4.getproperty('schared_m')), 1)
        self.assertIs(object4.getproperty('schared_m')[0], object2)

        self.assertEqual(len(object1.getproperty('schared_m')), 1)
        self.assertIs(object1.getproperty('schared_m')[0], object3)

        self.assertTrue(isinstance(object2.getproperty('schared23_u'), Object1))
        self.assertIs(object2.getproperty('schared23_u'), object4)
        self._del_objects()



