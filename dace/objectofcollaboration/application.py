from zope.interface import implementer
from substanced.root import Root, RootPropertySheet
from substanced.content import content

from .entity import Entity
from ..interfaces import IApplication


@implementer(IApplication)
class Application(Entity, Root):


    def __init__(self, **kwargs):
        super(Application, self).__init__(**kwargs)

