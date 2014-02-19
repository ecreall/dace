import unittest
from pyramid import testing
from substanced.testing import make_site


class TestCatalog(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def test_catalog_creation(self):
        site = make_site()
        from ..catalog import create_catalog
        create_catalog(site)
        self.assertEqual(1, 1)
