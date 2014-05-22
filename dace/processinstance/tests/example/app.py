from zope.interface import Interface
from pyramid.httpexceptions import HTTPFound
#from zope.authentication.interfaces import IAuthentication
#from zope.pluggableauth import PluggableAuthentication as PAU
#from com.ecreall.omegsi.library.authentication import initialize_pau

from dace.util import getWorkItem
from dace.catalog.interfaces import ISearchableObject
from dace.interfaces import IProcessDefinition



class Action(object):

    def __call__(self, form):
        work_item = getWorkItem('process_id', 'activity_id', form.request)
        work_item.lock()
        data = form.extractData()
        work_item.start(*data)


class StartALink(object):

    def render(self):
#        wi = getWorkItem('sample', 'a', self.request)
#        if wi is None:
#            return u""
        return u"""<a href="%s">%s</a>""" % (
                self.request.resource_url(self.context, '@@starta'),
                u"Start A")


class StartBLink(object):

    def render(self):
        # need the permission, the action context, the action context's state
        wi = getWorkItem('sample', 'b', self.request)
        if wi is None:
            return u""
        p_uid = ISearchableObject(wi).process_inst_uid()
        return u"""<a href="%s">%s</a>""" % (
                self.request.resource_url(self.context, '@@startb', query={'p_uid': p_uid}),
                u"Start B")


class StartCLink(object):

    def render(self):
        wi = getWorkItem('sample', 'c', self.request)
        if wi is None:
            return u""
        p_uid = ISearchableObject(wi).process_inst_uid()
        return u"""<a href="%s">%s</a>""" % (
                self.request.resource_url(self.context, '@@startc', {'p_uid': p_uid}),
                u"Start C")


class StartDLink(object):

    def render(self):
        # need the permission, the action context, the action context's state
        wi = getWorkItem('sample', 'd', self.request)
        if wi is None:
            return u""
        p_uid = ISearchableObject(wi).process_inst_uid()
        return u"""<a href="%s">%s</a>""" % (
                self.request.resource_url(self.context, '@@startd', {'p_uid': p_uid}),
                u"Start D")


class StartB(object):
    def render(self):
        wi = getWorkItem('sample', 'b', self.request)
        wi.start()
        return HTTPFound(self.request.resource_url(self.context,'@@index'))


class StartC(object):
    def render(self):
        wi = getWorkItem('sample', 'c', self.request)
        wi.start(['azerty', 'qwerty'])
        return HTTPFound(self.request.resource_url(self.context,'@@index'))


class StartD(object):
    def render(self):
        wi = getWorkItem('sample', 'd', self.request)
        wi.start()
        return HTTPFound(self.request.resource_url(self.context,'@@index'))


class StartA(object):
    def render(self):
        wi = getWorkItem('sample', 'a', self.request)
        wi.start()
        return HTTPFound(self.request.resource_url(self.context,'@@index'))
