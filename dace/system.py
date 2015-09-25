from zope.processlifetime import IDatabaseOpenedWithRoot
from .subscribers import start_ioloop


def includeme(config):
    config.add_subscriber(start_ioloop, IDatabaseOpenedWithRoot)
