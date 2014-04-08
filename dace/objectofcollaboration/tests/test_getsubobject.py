from dace.testing import FunctionalTests
from dace.util import (
    allSubobjectsOfType,
    allSubobjectsOfKind,
    subobjectsOfType,
    subobjectsOfKind)
from .example.objects import ObjectA, ObjectB, ObjectC, IObjectB, IObjectC


class TestRequest(FunctionalTests):

    def _create_objects(self):
        object1 = ObjectA()
        object2 = ObjectA()
        object3 = ObjectB()
        object4 = ObjectB()
        object5 = ObjectC()
     
        object2.setproperty('composition_m', [object5])
        object1.setproperty('composition_m', [object3, object4, object2])

        self.app['object1'] = object1

        return object1, object2, object3, object4, object5

    def test_allSubobjects(self):
        object1, object2, object3, object4, object5 = self._create_objects()
        result = allSubobjectsOfType(object1, IObjectB)

        self.assertEqual(len(result), 2)
        self.assertTrue((object3 in result))
        self.assertTrue((object4 in result))

        result = allSubobjectsOfKind(object1, IObjectB)

        self.assertEqual(len(result), 3)
        self.assertTrue((object3 in result))
        self.assertTrue((object4 in result))
        self.assertTrue((object5 in result))

        result = allSubobjectsOfType(object1, IObjectC)

        self.assertEqual(len(result), 1)
        self.assertTrue((object5 in result))

    def test_subobjects(self):
        object1, object2, object3, object4, object5 = self._create_objects()
        result = subobjectsOfType(object1, IObjectB)

        self.assertEqual(len(result), 2)
        self.assertTrue((object3 in result))
        self.assertTrue((object4 in result))

        result = subobjectsOfKind(object1, IObjectB)

        self.assertEqual(len(result), 2)
        self.assertTrue((object3 in result))
        self.assertTrue((object4 in result))

        result = subobjectsOfType(object1, IObjectC)

        self.assertEqual(len(result), 0)
