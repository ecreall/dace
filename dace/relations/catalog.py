from hypatia.catalog import Catalog
from hypatia.field import FieldIndex
from hypatia.keyword import KeywordIndex

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
    root['relations_container'] = RelationsContainer()
