from datetime import datetime, timedelta
import pytz

from dace import _


DEFAULT_LOCK_DURATION = timedelta(seconds=120)


class AlreadyLocked(Exception):
    pass


class LockableElement(object):
    _lock = (None, None)
    _lock_duration = DEFAULT_LOCK_DURATION

    def lock(self, request):
        """Raise AlreadyLocked if the activity was already locked by someone
        else.
        """
        if self.is_locked(request):
            raise AlreadyLocked(_(u"Already locked by ${user} at ${datetime}",
                mapping={'user': self._lock[0], 'datetime': self._lock[1]}))
        self._lock = (request.principal.id, datetime.now(pytz.utc))

    def unlock(self, request):
        """Raise AlreadyLocked if the activity was already locked by someone
        else.
        """
        if self.is_locked(request):
            raise AlreadyLocked(_(u"Already locked by ${user} at ${datetime}",
                mapping={'user': self._lock[0], 'datetime': self._lock[1]}))
        self._lock = (None, None)

    def is_locked(self, request):
        """If the activity was locked by the same user, return False.
        """
        if self._lock[1] is None:
            return False
        if self._lock[1] + self._lock_duration <= datetime.now(pytz.utc):
            return False
        if self._lock[0] == request.principal.id:
            return False
        return True

