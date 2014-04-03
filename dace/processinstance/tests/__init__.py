import os
import doctest
import unittest

import zope.event
from zope.component import testing


def tearDown(test):
    testing.tearDown(test)
    zope.event.subscribers.pop()

def setUp(test):
    test.globs['this_directory'] = os.path.dirname(__file__)
    testing.setUp(test)

def test_suite():
    suite = unittest.TestSuite()
#    suite.addTest(doctest.DocFileSuite(
#        'README.txt',
#        setUp=setUp, tearDown=tearDown,
#        optionflags=doctest.NORMALIZE_WHITESPACE))
    return suite
