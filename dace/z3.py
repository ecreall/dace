import sys
import time
import rwproperty

import transaction
#from zope.authentication.interfaces import IAuthentication
#from zope.component import getUtility
#from zope.component.hooks import getSite, setSite
from zope.interface import implements
#from zope.security.interfaces import IParticipation
#from zope.security.management import (
#    endInteraction, newInteraction, queryInteraction)
import ZODB.interfaces
from ZODB.POSException import ConflictError


class Participation(object):
#    implements(IParticipation)
    interaction = principal = None

    def __init__(self, principal):
        self.principal = principal


class BaseJob(object):
    # a job that examines the site and interaction participants when it is
    # created, and reestablishes them when run, tearing down as necessary.

    site_id = None
    participants = ()
    args = ()
    def __init__(self):
#    def __init__(self, *args, **kwargs):
#        self.callable = args[0]
#        self.args = args[1:]
#        self.kwargs = kwargs
        site = getSite()
        self.site_id = site.__name__
        self.database_name = site._p_jar.db().database_name
        interaction = queryInteraction()
        if interaction is not None:
            self.participants = tuple(
                participation.principal.id for participation in
                interaction.participations)

    def retry(self):
        transaction.begin()
#       self.callable(*self.args, **self.kwargs)
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
        db = getUtility(ZODB.interfaces.IDatabase, name=self.database_name)
        app = db.open().root()['Application']
        site = app[self.site_id]
        setSite(site)
        if self.participants:
            auth = getUtility(IAuthentication)
            newInteraction(
                *(Participation(auth.getPrincipal(principal_id)) for
                  principal_id in self.participants))
        return app

    def tearDown(self, app):
        setSite(None)
        endInteraction()
        app._p_jar.close()


class Job(BaseJob):
    _callable_oid = _callable_name = None

    @property
    def callable(self):
        site = getSite()
        callable_root = site._p_jar.get(self._callable_oid).eventKind
        call = getattr(callable_root, self._callable_name)
        return call

    @rwproperty.setproperty
    def callable(self, value):
        self._callable_oid = value.im_self.event._p_oid
        self._callable_name = value.__name__
