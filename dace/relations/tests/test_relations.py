from ..testing import FunctionalTests


class TestCatalog(FunctionalTests):

    def test_dace_catalog_creation(self):
        self.assertIn('dace', self.app['catalogs'])
#        connect(source, target, tags=tags)
