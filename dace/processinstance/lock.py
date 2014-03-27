from substanced.locking import(
    lock_resource,
    unlock_resource,
    could_lock_resource,
    LockError,
    UnlockError)

DEFAUT_DURATION = 3600

class LockableElement(object):

    def lock(self, request):
        """Raise AlreadyLocked if the activity was already locked by someone
        else.
        """
        try:
            lock_resource(self, request.user, DEFAUT_DURATION)
        except LockError:
            return

    def unlock(self, request):
        """Raise AlreadyLocked if the activity was already locked by someone
        else.
        """
        try:
            unlock_resource(self, request.user)
        except UnlockError:
            return

    def is_locked(self, request):
        """If the activity was locked by the same user, return False.
        """
        try:
            return not could_lock_resource(self, request.user)
        except LockError:
            return True
