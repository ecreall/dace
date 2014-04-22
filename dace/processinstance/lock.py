from substanced.locking import(
    lock_resource,
    unlock_resource,
    could_lock_resource,
    LockError,
    UnlockError)

DEFAUT_DURATION = 3600


def get_lock_operation(request):

    def _lock(obj):
        obj.lock(request)

    return _lock

def get_unlock_operation(request):

    def _unlock(obj):
        obj.unlock(request)

    return _unlock

class LockableElement(object):

    def __init__(self, **kwargs):
        super(LockableElement, self).__init__(**kwargs)
        self.dtlock = False
        self.tocall = []

    def call(self, obj):
        for c in self.tocall:
            c(obj)

        self.tocall = ()

    def lock(self, request):
        """Raise AlreadyLocked if the activity was already locked by someone
        else.
        """
        if self.dtlock:
            self.tocall.append(get_lock_operation(request))
            return

        try:
            lock_resource(self, request.user, DEFAUT_DURATION)
        except LockError:
            return

    def unlock(self, request):
        """Raise AlreadyLocked if the activity was already locked by someone
        else.
        """
        if self.dtlock:
            self.tocall.append(get_unlock_operation(request))
            return

        try:
            unlock_resource(self, request.user)
        except UnlockError:
            return

    def is_locked(self, request):
        """If the activity was locked by the same user, return False.
        """
        if self.dtlock:
            return False

        try:
            return not could_lock_resource(self, request.user)
        except LockError:
            return True
