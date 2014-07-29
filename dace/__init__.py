import logging
from pyramid.i18n import TranslationStringFactory
from substanced.sdi import user as sduser

log = logging.getLogger('dace')
_ =  TranslationStringFactory('dace')


class Anonymous(object):
    __name__ = 'Anonymous'
    locale = 'fr'


def user(request):
    result = sduser(request)
    if result is None:
        result = Anonymous()

    return result


import substanced.sdi
substanced.sdi.user = user


def includeme(config):
    config.scan()
#    config.add_request_method(user, reify=True)
