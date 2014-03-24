from dace.testing import FunctionalTests


class TestDaceCatalog(FunctionalTests):

    def test_dace_catalog_creation(self):
        self.assertIn('dace', self.app['catalogs'])
