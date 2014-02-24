from zope.container.contained import NameChooser as NC
from zope.interface import implements, Interface
from substanced.interfaces import IFolder
from ..util import adapter
from ..interfaces import INameChooser


@adapter(IFolder)
class NameChooser(NC):
    implements(INameChooser)
