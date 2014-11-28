# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Vincent Fretin, Amen Souissi

from zope.interface import Interface


class IObjectProvides(Interface):

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