# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Vincent Fretin, Amen Souissi

import logging
from pyramid.i18n import TranslationStringFactory


log = logging.getLogger('dace')
_ =  TranslationStringFactory('dace')


def includeme(config):
    config.scan()
#    config.add_request_method(user, reify=True)
