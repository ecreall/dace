import unittest

from pyramid.config import Configurator
from pyramid.testing import DummyRequest
from pyramid import testing

from substanced.db import root_factory


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings, root_factory=root_factory)
    return config.make_wsgi_app()


class FunctionalTests(unittest.TestCase):

    def setUp(self):
        import tempfile
        import os.path
        self.tmpdir = tempfile.mkdtemp()

        dbpath = os.path.join( self.tmpdir, 'test.db')
        uri = 'file://' + dbpath
        settings = {'zodbconn.uri': uri,
                    'substanced.secret': 'sosecret',
                    'substanced.initial_login': 'admin',
                    'substanced.initial_password': 'admin',
                    'pyramid.includes': [
            'pyramid_tm',
            'substanced',
            'dace',
        ]}

        app = main({}, **settings)
        self.db = app.registry._zodb_databases['']
        self.request = request = DummyRequest()
        self.config = testing.setUp(registry=app.registry, request=request)
        self.registry = self.config.registry
        self.app = root_factory(request)
        request.root = self.app
        self.users = self.app['principals']['users']
        self.app['principals'].add_user('alice', password='alice', email='alice@example.com')
        self.app['principals'].add_user('bob', password='bob', email='alice@example.com')
        request.user = self.users['admin']
        import dace.objectofcollaboration.principal.util
        dace.objectofcollaboration.principal.util.get_current_test = True
        self.def_container = self.app['process_definition_container']

    def tearDown(self):
        from dace.processinstance import event
        for dc_or_stream in event.callbacks.values():
            if hasattr(dc_or_stream, 'close'):
                dc_or_stream.close()
            else:
                dc_or_stream.stop()

        with event.callbacks_lock:
            event.callbacks = {}

        import shutil
        testing.tearDown()
        self.db.close()
        shutil.rmtree(self.tmpdir)
