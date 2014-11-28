# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Vincent Fretin, Amen Souissi
from dace.testing import FunctionalTests


class TestDaceCatalog(FunctionalTests):

    def test_dace_catalog_creation(self):
        self.assertIn('dace', self.app['catalogs'])
