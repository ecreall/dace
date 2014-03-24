from hypatia.catalog import Catalog
from hypatia.field import FieldIndex
from hypatia.keyword import KeywordIndex

from .container import RelationsContainer


def create_catalog(root):
    catalog = Catalog()
    catalog['source_id'] = FieldIndex('source_id')
    catalog['target_id'] = FieldIndex('target_id')
    catalog['state'] = FieldIndex('state')
    catalog['tags'] = KeywordIndex('tags')
    catalog['from_interfaces_flattened'] = KeywordIndex('from_interfaces_flattened')
    catalog['to_interfaces_flattened'] = KeywordIndex('to_interfaces_flattened')
    root['relations'] = catalog
    root['relations_container'] = RelationsContainer()
