"""Reactor bootstrap: subscribe ``start_ioloop`` to
``IDatabaseOpenedWithRoot`` so the tornado IOLoop and the zmq job
consumer start as soon as the ZODB is opened (see
docs/en/architecture.md, section 6).
"""
from zope.processlifetime import IDatabaseOpenedWithRoot
from .subscribers import start_ioloop


def includeme(config):
    config.add_subscriber(start_ioloop, IDatabaseOpenedWithRoot)
