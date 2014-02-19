from zope.interface import Interface


class IObjectProvides(Interface):

    def object_provides():
        pass


class ISearchableObject(Interface):

    def process_id():
        pass

    def node_id():
        pass

    def process_inst_uid():
        pass

    def context_id():
        pass
