from zope.processlifetime import IDatabaseOpenedWithRoot
from .subscribers import start_ioloop, start_intermediate_events


def includeme(config):
    config.add_subscriber(start_ioloop, IDatabaseOpenedWithRoot)
    config.add_subscriber(start_intermediate_events, IDatabaseOpenedWithRoot)
