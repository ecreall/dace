# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Vincent Fretin, Amen Souissi
from hypatia.catalog import Catalog
from hypatia.field import FieldIndex
from hypatia.keyword import KeywordIndex
from substanced.interfaces import IService
from zope.interface import alsoProvides

from .container import RelationsContainer


def create_catalog(root):
    catalog = Catalog()
    catalog['source_id'] = FieldIndex('source_id')
    catalog['target_id'] = FieldIndex('target_id')
    catalog['relation_id'] = FieldIndex('relation_id')
    catalog['reftype'] = FieldIndex('reftype')
    catalog['tags'] = KeywordIndex('tags')
    catalog['from_interfaces_flattened'] = KeywordIndex('from_interfaces_flattened')
    catalog['to_interfaces_flattened'] = KeywordIndex('to_interfaces_flattened')
    root['relations'] = catalog
    alsoProvides(catalog, IService)
    root['relations_container'] = RelationsContainer()
