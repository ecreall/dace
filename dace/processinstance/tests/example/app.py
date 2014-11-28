# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi

from pyramid.httpexceptions import HTTPFound

from dace.util import getWorkItem
from dace.catalog.interfaces import ISearchableObject




class Action(object):

    def __call__(self, form):
        work_item = getWorkItem(None, form.request, 'process_id', 'activity_id')
        work_item.lock()
        data = form.extractData()
        work_item.start(*data)


class StartALink(object):

    def render(self):
        return u"""<a href="%s">%s</a>""" % (
                self.request.resource_url(self.context, '@@starta'),
                u"Start A")


class StartBLink(object):

    def render(self):
        # need the permission, the action context, the action context's state
        wi = getWorkItem(None, self.request, 'sample', 'b')
        if wi is None:
            return u""
        p_uid = ISearchableObject(wi).process_inst_uid()
        return u"""<a href="%s">%s</a>""" % (
                self.request.resource_url(self.context, '@@startb', query={'p_uid': p_uid}),
                u"Start B")


class StartCLink(object):

    def render(self):
        wi = getWorkItem(None, self.request, 'sample', 'c')
        if wi is None:
            return u""
        p_uid = ISearchableObject(wi).process_inst_uid()
        return u"""<a href="%s">%s</a>""" % (
                self.request.resource_url(self.context, '@@startc', {'p_uid': p_uid}),
                u"Start C")


class StartDLink(object):

    def render(self):
        # need the permission, the action context, the action context's state
        wi = getWorkItem(None, self.request, 'sample', 'd')
        if wi is None:
            return u""
        p_uid = ISearchableObject(wi).process_inst_uid()
        return u"""<a href="%s">%s</a>""" % (
                self.request.resource_url(self.context, '@@startd', {'p_uid': p_uid}),
                u"Start D")


class StartB(object):
    def render(self):
        wi = getWorkItem(None, self.request, 'sample', 'b')
        wi.start()
        return HTTPFound(self.request.resource_url(self.context,'@@index'))


class StartC(object):
    def render(self):
        wi = getWorkItem(None, self.request, 'sample', 'c')
        wi.start(['azerty', 'qwerty'])
        return HTTPFound(self.request.resource_url(self.context,'@@index'))


class StartD(object):
    def render(self):
        wi = getWorkItem(None, self.request, 'sample', 'd')
        wi.start()
        return HTTPFound(self.request.resource_url(self.context,'@@index'))


class StartA(object):
    def render(self):
        wi = getWorkItem(None, self.request, 'sample', 'a')
        wi.start()
        return HTTPFound(self.request.resource_url(self.context,'@@index'))
