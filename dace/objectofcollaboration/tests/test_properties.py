from pyramid.threadlocal import get_current_registry
from substanced.util import get_oid, is_service

from dace.relations import connect, disconnect, RelationValue
from dace.relations import find_relations
from dace.relations import get_relations_catalog
from dace.relations import get_relations_container
from dace.testing import FunctionalTests
from dace.objectofcollaboration.object import (
                COMPOSITE_UNIQUE, 
                SHARED_UNIQUE,
                COMPOSITE_MULTIPLE,
                SHARED_MULTIPLE,
                Object)


class Object1(Object):
    properties_def = {'composition_u':(COMPOSITE_UNIQUE, 'schared2_u', False),
                      'composition_m':(COMPOSITE_MULTIPLE, 'schared21_u', False),
                      'schared_u':(SHARED_UNIQUE, 'schared22_u', False),
                      'schared_m':(SHARED_MULTIPLE, 'schared23_u', False)}

    def __init__(self, **kwargs):
        Object.__init__(self, **kwargs)


class Object2(Object):
    properties_def = {'schared2_u':(SHARED_UNIQUE, 'composition_u', False),
                      'schared21_u':(SHARED_UNIQUE, 'composition_m', False),
                      'schared22_u':(SHARED_UNIQUE, 'schared_u', False),
                      'schared23_u':(SHARED_UNIQUE, 'schared_m', False)}

    def __init__(self, **kwargs):
        Object.__init__(self, **kwargs)


class TestProperties(FunctionalTests):

    def test_properties_creation(self):
        self.assertIn('relations', self.app)
        self.assertIn('relations_container', self.app)
        catalog = get_relations_catalog()
        self.assertIsNotNone(catalog)
        self.assertTrue(is_service(get_relations_catalog()))
        self.assertTrue(is_service(get_relations_container()))

    def _create_objects_cu_su(self):
        registry = get_current_registry()
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

    def _create_objects_cm_su(self):
        registry = get_current_registry()
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


    def _create_objects_su_su(self):
        registry = get_current_registry()
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


    def _create_objects_sm_su(self):
        registry = get_current_registry()
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



