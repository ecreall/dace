import logging
from pyramid.i18n import TranslationStringFactory


log = logging.getLogger('dace')
_ =  TranslationStringFactory('dace')


def includeme(config):
    config.scan()
#    config.add_request_method(user, reify=True)
