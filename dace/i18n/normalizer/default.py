# -*- coding: UTF-8 -*-

from zope.interface import implementer

from dace.i18n.normalizer.interfaces import INormalizer
from dace.i18n.normalizer.base import mapUnicode
from dace.util import utility

# French character mapping
mapping = {
    339: 'oe'
}


@utility(name='default_normalizer')
@implementer(INormalizer)
class Normalizer(object):
    """
    This normalizer can normalize any unicode string and returns a version
    that only contains of ASCII characters.

    Let's make sure that this implementation actually fulfills the API.

      >>> from zope.interface.verify import verifyClass
      >>> verifyClass(INormalizer, Normalizer)
      True
    """

    def normalize(self, text, locale=None, max_length=None):
        """
        Returns a normalized text. text has to be a unicode string.
        """
        return mapUnicode(text, mapping=mapping)


normalizer = Normalizer()
