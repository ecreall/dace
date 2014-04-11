import sys
import time
import rwproperty

import transaction
from ZODB.POSException import ConflictError

from pyramid.threadlocal import get_current_registry, get_current_request
from pyramid import testing
from pyramid.testing import DummyRequest
from substanced.util import get_oid
from substanced.interfaces import IUserLocator
from substanced.principal import DefaultUserLocator


class BaseJob(object):
    # a job that examines the site and interaction participants when it is
    # created, and reestablishes them when run, tearing down as necessary.

    args = ()
    def __init__(self):
        request = get_current_request()
        self.site_id = 'app_root'
        self.database_name = request.root._p_jar.db().database_name
        self.userid = get_oid(request.user)
        self.registry = get_current_registry()
        # Job can't be persisted with this self.registry

    def retry(self):
        transaction.begin()
        self.callable(*self.args)
        transaction.commit()

    def __call__(self):
        # log here don't work, we are in the eventloop
        try:
            app = self.setUp()
            self.retry()
        except ConflictError:
            transaction.abort()
            print "ConflictError, retry in 2s"
            time.sleep(2.0)
            self.retry()
        except Exception:
            transaction.abort()
            print "transaction abort, so retry aborted"
            print sys.exc_info()
            print self.callable
            raise
        finally:
            self.tearDown(app)

    def setUp(self):
        db = self.registry._zodb_databases[self.database_name]
        app = db.open().root()[self.site_id]
        request = DummyRequest()
        testing.setUp(registry=self.registry, request=request)
        request.root = app
        locator = self.registry.queryMultiAdapter((app, request),
                                                  IUserLocator)
        if locator is None:
            locator = DefaultUserLocator(app, request)

        user = locator.get_user_by_userid(self.userid)
        request.user = user
        return app

    def tearDown(self, app):
        testing.tearDown()
        app._p_jar.close()


class Job(BaseJob):
    _callable_oid = _callable_name = None

    @property
    def callable(self):
        request = get_current_request()
        site = request.root
        callable_root = site._p_jar.get(self._callable_oid).eventKind
        call = getattr(callable_root, self._callable_name)
        return call

    @rwproperty.setproperty
    def callable(self, value):
        self._callable_oid = value.im_self.event._p_oid
        self._callable_name = value.__name__
