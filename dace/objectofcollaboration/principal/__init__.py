from substanced.principal import User as OriginUser
from ..entity import Entity

class User(OriginUser, Entity):

    def __init__(self, password=None, email=None, tzname=None, locale=None, **kwargs):
        OriginUser.__init__(self, password, email, tzname, locale)
        Entity.__init__(self, kwargs)

