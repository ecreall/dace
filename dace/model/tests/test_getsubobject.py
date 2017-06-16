# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi
from dace.testing import FunctionalTests
from dace.util import (
    all_subobjects_of_type,
    all_subobjects_of_kind,
    subobjects_of_type,
    subobjects_of_kind)
from .example.objects import ObjectA, ObjectB, ObjectC, IObjectB, IObjectC


class TestRequest(FunctionalTests):

    def _del_objects(self):
        try:
            self.app.remove('object1')
        except:
            pass

    def _create_objects(self):
        object1 = ObjectA()
        object2 = ObjectA()
        object3 = ObjectB()
        object4 = ObjectB()
        object5 = ObjectC()

        object2.setproperty('composition_mu', [object5])
        object1.setproperty('composition_mu', [object3, object4, object2])

        self.app['object1'] = object1

        return object1, object2, object3, object4, object5

    def test_allSubobjects(self):
        object1, object2, object3, object4, object5 = self._create_objects()
        result = list(all_subobjects_of_type(object1, IObjectB))

        self.assertEqual(len(result), 2)
        self.assertTrue((object3 in result))
        self.assertTrue((object4 in result))

        result = list(all_subobjects_of_kind(object1, IObjectB))

        self.assertEqual(len(result), 3)
        self.assertTrue((object3 in result))
        self.assertTrue((object4 in result))
        self.assertTrue((object5 in result))

        result = list(all_subobjects_of_type(object1, IObjectC))

        self.assertEqual(len(result), 1)
        self.assertTrue((object5 in result))
        self._del_objects()

    def test_subobjects(self):
        object1, object2, object3, object4, object5 = self._create_objects()
        result = list(subobjects_of_type(object1, IObjectB))

        self.assertEqual(len(result), 2)
        self.assertTrue((object3 in result))
        self.assertTrue((object4 in result))

        result = list(subobjects_of_kind(object1, IObjectB))

        self.assertEqual(len(result), 2)
        self.assertTrue((object3 in result))
        self.assertTrue((object4 in result))

        result = list(subobjects_of_type(object1, IObjectC))

        self.assertEqual(len(result), 0)
        self._del_objects()
