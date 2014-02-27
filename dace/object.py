from zope.interface import implements
import colander

from .interfaces import IObject


class Object(object):
    implements(IObject)

    def __init__(self):
        super(Object, self).__init__()
        self.__property__ = None

    def get_data(self, node):
        result = {}
        for child in node:
            name = child.name
            val = getattr(self, name, colander.null)
            result[name] = val
        return result

    def set_data(self, appstruct):
        for name, val in appstruct.items():
            if hasattr(self, name):
                existing_val = getattr(self, name, None)
                new_val = appstruct[name]
                if existing_val != new_val:
                    setattr(self, name, new_val)

    def url(self, request, view=None, args=None):
        if view is None:
            #generalement c est la vue de l index associer qu'il faut retourner
            return request.mgmt_path(self, '@@contents')
        else:
            return request.mgmt_path(self, '@@'+view)
