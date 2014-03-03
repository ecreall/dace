from persistent import Persistent
from pyramid.threadlocal import get_current_registry
from pyramid.interfaces import ILocation
from pyramid.events import subscriber
from zope.interface import implements, Attribute
from zope.component import createObject
from substanced.event import ObjectAdded
import thread

from dace.interfaces import IRuntime, IProcessStarted, IProcessFinished
from dace.processinstance.workitem import DecisionWorkItem, StartWorkItem
from dace.processinstance.core import EventHandler
from dace import log


#TODO
#class RuntimeNameChooser(NameChooser, grok.Adapter):
#    grok.context(IRuntime)
#    grok.implements(INameChooser)


class BPMNElementDefinition(object):
    pass


class FlowNodeDefinition(BPMNElementDefinition):
    factory = Attribute("factory")
    incoming = ()
    outgoing = ()
    __name__ = None
    performer = ''
    process = None

    def create(self, process):
        return self.factory(process, self)

    def transitionOutgoing(self, transition):
        self.transition_outgoing += (transition,)
        self.computeOutgoing()

    def __init__(self):
        super(FlowNodeDefinition, self).__init__()
        self.incoming = self.outgoing = ()
        self.transition_outgoing = self.explicit_outgoing = ()
        self.applications = ()

    def addApplication(self, application, actual=()):
        app = self.process.applications[application]
        formal = app.parameters
        if len(formal) != len(actual):
            raise TypeError("Wrong number of parameters => "
                            "Actual=%s, Formal=%s for Application %s with id=%s"
                            %(actual, formal, app, app.id))
        self.applications += ((application, formal, tuple(actual)), )

    def addOutgoing(self, transition_id):
        self.explicit_outgoing += (transition_id,)
        self.computeOutgoing()

    def computeOutgoing(self):
        if self.explicit_outgoing:
            transitions = dict([(t.id, t) for t in self.transition_outgoing])
            self.outgoing = ()
            for tid in self.explicit_outgoing:
                transition = transitions.get(tid)
                if transition is not None:
                    self.outgoing += (transition,)
        else:
            self.outgoing = self.transition_outgoing

    def createStartWorkItems(self, nodedef, node_ids):
        for application, formal, actual in self.applications:
            workitem = StartWorkItem(application, nodedef, node_ids)
            yield workitem

    def __repr__(self):
        return "<%s %r>" % (self.__class__.__name__, self.__name__)


class EventHandlerDefinition(FlowNodeDefinition):
    factory = EventHandler
    boundaryEvents = ()


class InvalidProcessDefinition(Exception):
    """A process definition isn't valid in some way.
    """
