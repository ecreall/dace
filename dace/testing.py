# Copyright (c) 2014 by Ecreall under licence AGPL terms
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Vincent Fretin, Amen Souissi

"""Functional test harness.

``FunctionalTests`` builds a real Pyramid app (substanced + dace) on a
temporary file ZODB, applies the request extensions so
``request.user`` works, creates alice/bob, logs in as admin and
exposes ``def_container``; ``tearDown`` stops the reactor and removes
the database.
"""
import unittest

from pyramid.config import Configurator
from pyramid.testing import DummyRequest
from pyramid.interfaces import IRequestExtensions
from pyramid import testing
from pyramid.interfaces import IAuthenticationPolicy
from pyramid.threadlocal import get_current_request

from substanced.db import root_factory

from dace.util import get_userid_by_login
from dace.subscribers import stop_ioloop


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings, root_factory=root_factory)
    return config.make_wsgi_app()


class _TestingAuthenticationPolicy(object):
    """Minimal authentication policy for the harness.

    Replaces ``pyramid.tests.test_security._registerAuthenticationPolicy``,
    which modern pyramid wheels no longer ship (Phase 3): every request
    authenticates as the configured ``userid``.
    """

    def __init__(self, userid):
        self.userid = userid

    def authenticated_userid(self, request):
        return self.userid

    def unauthenticated_userid(self, request):
        return self.userid

    def effective_principals(self, request):
        return [self.userid]

    def remember(self, request, userid, **kw):
        return []

    def forget(self, request):
        return []


def login(login):
    """Point the test authentication policy at the user of ``login``."""
    request = get_current_request()
    userid = get_userid_by_login(login, request)
    request.registry.registerUtility(
        _TestingAuthenticationPolicy(userid), IAuthenticationPolicy)
    # request.authenticated_userid will now return the oid of the user object


class FunctionalTests(unittest.TestCase):

    """Base class of the functional layers (see module docstring)."""
    def setUp(self):
        """Build the throwaway app and log in as admin."""
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
        self.request.test = True
        self.config = testing.setUp(registry=app.registry, request=request)

        # set extensions (add_request_method, so the request.user works)
        extensions = app.registry.queryUtility(IRequestExtensions)
        if extensions is not None:
            if getattr(request, '_set_extensions', None) is not None:  # pyramid 1.5.7
                request._set_extensions(extensions)
            else:
                from pyramid.request import apply_request_extensions
                apply_request_extensions(request, extensions=extensions)

        self.registry = self.config.registry
        self.app = root_factory(request)
        request.root = request.context = self.app
        # request.user execute substanced.sdi.user which get request.context to find objectmap
        self.users = self.app['principals']['users']
        self.app['principals'].add_user('alice',
                                        password='alice',
                                        email='alice@example.com')
        self.app['principals'].add_user('bob',
                                        password='bob',
                                        email='alice@example.com')
        login('admin')
        # request.user is the admin user, but if you do later login('system'), you will still have admin in request.user
        #request.user = self.users['admin']
        self.def_container = self.app['process_definition_container']

    def tearDown(self):
        """Stop the reactor, tear down, delete the temporary database."""
        stop_ioloop()
        import shutil
        testing.tearDown()
        self.db.close()
        shutil.rmtree(self.tmpdir)
