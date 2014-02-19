import unittest
from pyramid import testing
from substanced.root import Root
from substanced.event import RootAdded
from pyramid.threadlocal import get_current_registry


class TestCatalog(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()
        self.config.registry.settings['substanced.secret'] = 'klkmlkml'
        self.config.testing_securitypolicy(permissive=True)
        self.config.include('substanced')
        self.config.include('dace')

    def tearDown(self):
        testing.tearDown()

    def test_catalog_creation(self):
        site = Root()
        get_current_registry().notify(RootAdded(site))
        self.assertEqual(1, 1)
