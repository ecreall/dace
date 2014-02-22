import logging
from pyramid.i18n import TranslationStringFactory

log = logging.getLogger('dace')
_ =  TranslationStringFactory('dace')

def includeme(config): # pragma: no cover
    config.scan()
