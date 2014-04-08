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
        request.user = self.app.data['principals'].data['users'].data['admin']
#        from webtest import TestApp
#        self.testapp = TestApp(app)

    def tearDown(self):
        import shutil
        testing.tearDown()
        self.db.close()
        shutil.rmtree(self.tmpdir)
