# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Vincent Fretin, Amen Souissi

"""The two adapter contracts feeding the dace catalog indexes."""
from zope.interface import Interface


class IObjectProvides(Interface):

    """Identity/containment vocabulary of any object."""
    def object_provides():
        pass

    def object_type():
        pass

    def containers_oids():
        pass

    def container_oid():
        pass   

    def oid():
        pass    


class ISearchableObject(Interface):

    """Process vocabulary of engine objects (work-items, actions, processes)."""
    def process_id():
        pass

    def process_discriminator():
        pass

    def node_id():
        pass

    def process_inst_uid():
        pass

    def context_id():
        pass

    def context_provides():
        pass

    def isautomatic():
        pass

    def issystem():
        pass

    def potential_contexts_ids():
        pass