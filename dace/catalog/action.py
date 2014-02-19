from substanced.catalog import (
    catalog_factory,
    Field,
    Keyword,
    Allowed,
    Text,
    )


@catalog_factory('searchableworkItem')
class SearchableWorkItemFactory(object):
    grok.context(ISearchableWorkItem)

    process_id = Field()
    node_id = Field()
    process_inst_uid = Set()
    context_id = Set()
