# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Vincent Fretin, Amen Souissi
"""Creation of the relation catalog and its container.

Seven indexes: the field indexes ``source_id``/``target_id``/
``relation_id``/``reftype`` and the keyword indexes ``tags`` and the
flattened interfaces of both ends.
"""
from hypatia.catalog import Catalog
from hypatia.field import FieldIndex
from hypatia.keyword import KeywordIndex
from substanced.interfaces import IService
from zope.interface import alsoProvides

from .container import RelationsContainer


def create_catalog(root):
    """Install ``root['relations']`` (7 indexes) and ``root['relations_container']``."""
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
