
import unidecode


def mapUnicode(text, mapping={}):
    """
    This method is used for replacement of special characters found in a
    mapping before baseNormalize is applied.
    """
    # always apply base normalization
    return baseNormalize(u''+''.join(
        [mapping.get(ord(ch), ch) for ch in text]))


def baseNormalize(text):
    """
        This method is used for normalization of unicode characters to the base ASCII
        letters. Output is ASCII encoded string (or char) with only ASCII letters,
        digits, punctuation and whitespace characters. Case is preserved.

          >>> baseNormalize(123)
          '123'

          >>> baseNormalize(u'a\u0fff')
          'a'

          >>> baseNormalize(u"foo\N{LATIN CAPITAL LETTER I WITH CARON}")
          'fooI'

          >>> baseNormalize(u"\u5317\u4EB0")
          'Bei Jing '
    """

    if not isinstance(text, str):
        # This most surely ends up in something the user does not expect
        # to see. But at least it does not break.
        return repr(text)

    return unidecode.unidecode(text.strip()).encode('ascii')
