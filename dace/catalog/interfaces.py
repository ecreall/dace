from zope.interface import Interface


class IObjectProvides(Interface):

    def object_provides():
        pass

    def object_type():
        pass

    def containers_oids():
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
