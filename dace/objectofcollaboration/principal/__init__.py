# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message
from pyramid.renderers import render

from substanced.principal import User as OriginUser
from substanced.util import (
    find_service,
    acquire,
    )

from ..entity import Entity


class User(OriginUser, Entity):

    def __init__(self, password=None, email=None, tzname=None, locale=None, **kwargs):
        OriginUser.__init__(self, password, email, tzname, locale)
        Entity.__init__(self, **kwargs)

    def email_password_reset(self, request):
        """ Sends a password reset email."""
        root = request.virtual_root
        sitename = acquire(root, 'title', None) or 'Dace'
        principals = find_service(self, 'principals')
        reset = principals.add_reset(self)
        # XXX should this really point at an SDI URL?
        reseturl = request.resource_url(reset)
        if not self.email:
            raise ValueError('User does not possess a valid email address.')
        message = Message(
            subject = 'Account information for %s' % sitename,
            recipients = [self.email],
            body = render('dace:objectofcollaboration/principal/templates/resetpassword_email.pt',
                          dict(reseturl=reseturl))
            )
        mailer = get_mailer(request)
        mailer.send(message)


class Machine(User):
    pass
