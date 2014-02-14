from zc.relation import any
from .values import RelationValue

def includeme(config): # pragma: no cover
    config.scan('.subscribers')
