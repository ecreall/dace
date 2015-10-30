from zope.interface import Interface


class INormalizer(Interface):
    """A normalizer can normalize any unicode text string according to a
       specific ruleset implemented in the normalizer itself.
    """

    def normalize(text, locale=None, max_length=None):
        """The normalize method takes and input unicode text and an optional
           locale string and returns a normalized version of the text.
           If the locale is not None the ouput might differ dependent on the
           locale. The max_length argument allows you to override the default
           values used by the normalizers on a case-by-case basis.
        """