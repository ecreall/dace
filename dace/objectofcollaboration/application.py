
from zope.interface import implementer
from substanced.root import Root

from dace.objectofcollaboration.entity import Entity
from dace.interfaces import IApplication


@implementer(IApplication)
class Application(Entity, Root):

    def __init__(self, **kwargs):
        super(Application, self).__init__(**kwargs)
