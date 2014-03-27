from pyramid.threadlocal import get_current_registry
from substanced.util import get_oid, is_service

from dace.relations import connect, disconnect, RelationValue
from dace.relations import find_relations
from dace.relations import get_relations_catalog
from dace.relations import get_relations_container
from dace.testing import FunctionalTests



class TestRelationsCatalog(FunctionalTests):

    def test_catalog_creation(self):
        self.assertIn('relations', self.app)
        self.assertIn('relations_container', self.app)
        catalog = get_relations_catalog()
        self.assertIsNotNone(catalog)
        self.assertTrue(is_service(get_relations_catalog()))
        self.assertTrue(is_service(get_relations_container()))

    def _create_relation(self):
        registry = get_current_registry()
        self.app['folder1'] = registry.content.create('Folder')
        self.app['folder2'] = registry.content.create('Folder')
        source = self.app['folder1']
        target = self.app['folder2']
        relation = connect(source, target, tags=[u'created'])
        return source, target, relation

    def test_find_relations(self):
        source, target, relation = self._create_relation()
        results = list(find_relations({'source_id': get_oid(source)}))
        self.assertEqual(len(results), 1)
        self.assertTrue(isinstance(results[0], RelationValue))
        self.assertIs(results[0].source, source)
        self.assertIs(results[0].target, target)

        results = find_relations({'target_id': get_oid(target)})
        self.assertEqual(len(list(results)), 1)

        results = find_relations({'tags': ('any', (u'created', u'involved'))})
        self.assertEqual(len(list(results)), 1)

        results = find_relations({'tags': ('all', (u'created', u'involved'))})
        self.assertEqual(len(list(results)), 0)

        results = find_relations({'tags': u'created'})
        self.assertEqual(len(list(results)), 1)

        results = find_relations({'tags': u'involved'})
        self.assertEqual(len(list(results)), 0)

    def test_disconnect_relation(self):
        source, target, relation = self._create_relation()
        self.assertEqual(len(get_relations_container()), 1)
        results = find_relations({'target_id': get_oid(target)})

        disconnect(relation)
        self.assertEqual(len(get_relations_container()), 0)
        results = find_relations({'target_id': get_oid(target)})
        self.assertEqual(len(list(results)), 0)

    def test_remove_source(self):
        source, target, relation = self._create_relation()
        self.assertEqual(len(get_relations_container()), 1)
        results = find_relations({'target_id': get_oid(target)})
        self.assertEqual(len(list(results)), 1)

        del source.__parent__[source.__name__]
        self.assertEqual(len(get_relations_container()), 0)
        results = find_relations({'target_id': get_oid(target)})
        self.assertEqual(len(list(results)), 0)

    def test_remove_target(self):
        source, target, relation = self._create_relation()
        self.assertEqual(len(get_relations_container()), 1)
        results = find_relations({'target_id': get_oid(target)})
        self.assertEqual(len(list(results)), 1)

        del target.__parent__[target.__name__]
        self.assertEqual(len(get_relations_container()), 0)
        results = find_relations({'target_id': get_oid(target)})
        self.assertEqual(len(list(results)), 0)
