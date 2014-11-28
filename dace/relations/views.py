# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Vincent Fretin, Amen Souissi

from substanced.sdi import mgmt_view
from substanced.sdi import LEFT

from .values import RelationValue



@mgmt_view(
    name = 'Vue',
    context=RelationValue,
    renderer='templates/relation_view.pt',
    tab_near=LEFT
    )
class RelationValueView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def _source(self):
        source = self.context.source
        source_url = {}
        if source is not None:
            source_url = {'url':source.url(self.request), 'title':source.title} 
        return source_url

    def _target(self):
        target = self.context.target
        target_url = {}
        if target is not None:
            target_url = {'url':target.url(self.request), 'title':target.title} 
        return target_url

    def __call__(self):
       result = {
                'relation_id': self.context.relation_id,
                'reftype': self.context.reftype,
                'source': self._source(),
                'target': self._target(),
                'tags': self.context.tags,
               }
       return result

