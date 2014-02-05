from zope.interface import implements

from .interfaces import ITransitionDefinition


def always_true(data):
    return True


class TransitionDefinition(object):
    implements(ITransitionDefinition)

    def __init__(self, from_, to, condition=always_true, sync=False):
        self.id = '%s-%s' % (from_, to)
        self.from_ = from_
        self.to = to
        self.condition = condition
        self.sync = sync

    def __repr__(self):
        return "%s(from=%r, to=%r)" % (self.__class__.__name__,
                self.from_, self.to)
