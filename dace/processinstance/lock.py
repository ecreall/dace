# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi

from substanced.locking import (lock_resource,
                                unlock_resource,
                                could_lock_resource,
                                LockError,
                                UnlockError)

from dace.objectofcollaboration.principal.util import get_current, Anonymous

DEFAUT_DURATION = 3600


def get_lock_operation(request):

    def _lock(obj):
        obj.lock(request)

    return _lock


def get_unlock_operation(request):

    def _unlock(obj):
        obj.unlock(request)

    return _unlock


def get_useroruseroid(request):
    user = get_current(request)
    if isinstance(user, Anonymous):
        user = user.oid 

    return user 


class LockableElement(object):

    def __init__(self, **kwargs):
        super(LockableElement, self).__init__(**kwargs)
        self.dont_lock = False
        self.callbacks = []

    def call(self, obj):
        for callback in self.callbacks:
            callback(obj)

        self.callbacks = ()

    def lock(self, request):
        """Raise AlreadyLocked if the activity was already locked by someone
        else.
        """
        if getattr(self, 'dont_lock', False):
            self.callbacks.append(get_lock_operation(request))
            return

        try:
            user = get_current(request)
            if isinstance(user, Anonymous):
                 return

            lock_resource(self, user, DEFAUT_DURATION)
        except LockError:
            return

    def unlock(self, request):
        """Raise AlreadyLocked if the activity was already locked by someone
        else.
        """
        if getattr(self, 'dont_lock', False):
            self.callbacks.append(get_unlock_operation(request))
            return

        try:
            user = get_current(request)
            if isinstance(user, Anonymous):
                 return

            unlock_resource(self, user)
        except UnlockError:
            return

    def is_locked(self, request):
        """If the activity was locked by the same user, return False.
        """
        if getattr(self, 'dont_lock', False):
            return False

        user = get_current(request)
        if isinstance(user, Anonymous):
             return False

        try:
            return not could_lock_resource(self, user)
        except ValueError:  # self is probably an action not bound to zodb
            return False
        except LockError:
            return True
