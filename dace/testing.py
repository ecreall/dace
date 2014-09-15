import unittest

from pyramid.config import Configurator
from pyramid.testing import DummyRequest
from pyramid.interfaces import IRequestExtensions
from pyramid import testing
from pyramid.tests.test_security import _registerAuthenticationPolicy
from pyramid.threadlocal import get_current_request

from substanced.db import root_factory

from dace.util import get_userid_by_login


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings, root_factory=root_factory)
    return config.make_wsgi_app()


def login(login):
    request = get_current_request()
    userid = get_userid_by_login(login, request)
    _registerAuthenticationPolicy(request.registry, userid)
    # request.authenticated_userid will now return the oid of the user object


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

        # set extensions (add_request_method, so the request.user works)
        extensions = app.registry.queryUtility(IRequestExtensions)
        if extensions is not None:
            request._set_extensions(extensions)

        self.registry = self.config.registry
        self.app = root_factory(request)
        request.root = request.context = self.app
        # request.user execute substanced.sdi.user which get request.context to find objectmap
        self.users = self.app['principals']['users']
        self.app['principals'].add_user('alice', password='alice', email='alice@example.com')
        self.app['principals'].add_user('bob', password='bob', email='alice@example.com')
        login('admin')
        # request.user is the admin user, but if you do later login('system'), you will still have admin in request.user
        #request.user = self.users['admin']
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

        from dace.objectofcollaboration.system import CRAWLERS
        for crawler in CRAWLERS:
            crawler.stop()

        import shutil
        testing.tearDown()
        self.db.close()
        shutil.rmtree(self.tmpdir)
