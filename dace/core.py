import thread
from datetime import datetime, timedelta
import pytz
from persistent import Persistent
from zope.container.interfaces import INameChooser
from zope.container.contained import NameChooser
from zope.interface import implements, Attribute
from zope.component import createObject
from zope.event import notify
from zope.lifecycleevent import ObjectAddedEvent
from zope.location.interfaces import ILocation

import grok

from .interfaces import IRuntime, IProcessStarted, IProcessFinished
from .workitem import DecisionWorkItem, StartWorkItem
from .wizard import WizardStep
from . import log, _



class RuntimeNameChooser(NameChooser, grok.Adapter):
    grok.context(IRuntime)
    grok.implements(INameChooser)


class BPMNElementDefinition(object):
    pass


class BPMNElement(object):
    def __init__(self, definition):
        self.id = definition.id


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


class FlowNode(BPMNElement, Persistent):
    implements(ILocation)
    workitems = None

    @property
    def __parent__(self):
        return self.process

    @property
    def __name__(self):
        return self.id

    def __init__(self, process, definition):
        super(FlowNode, self).__init__(definition)
        self.process = process
        self.workitems = {}

    def prepare(self):
        notify(ActivityPrepared(self))

    def __call__(self, transition):
        self.start(transition)

    def start(self, transition):
        raise NotImplementedError

    def stop(self):
        pass

    @property
    def definition(self):
        return self.process.definition.activities[self.id]

    def _createWorkItems(self, gw, node_ids):
        for application, formal, actual in self.definition.applications:
            workitem = DecisionWorkItem(application, gw, node_ids, self)
            yield workitem, application, formal, actual

    def _define_next_replay_node(self):
        self._v_next_replay_node = None
        if hasattr(self.process, '_v_toreplay') and \
           self.process._v_toreplay and \
           self.id == self.process._v_toreplay[0]:
            self.process._v_toreplay = self.process._v_toreplay[1:]
            if self.process._v_toreplay:
                self._v_next_replay_node = self.process._v_toreplay[0]

    def __repr__(self):
        return "%s(%r)" % (
            self.__class__.__name__,
            self.process.id + '.' +
            self.id
            )

    def _finish(self):
        notify(ActivityFinished(self))

        definition = self.definition

        transitions = []
        for transition in definition.outgoing:
            bypass_condition = hasattr(self, '_v_next_replay_node') and \
                    transition.to == self._v_next_replay_node
            # bypass condition on replay mode
            if bypass_condition or \
                    transition.sync or \
                    transition.condition(self.process):
                transitions.append(transition)

        self.process.transition(self, transitions)



class WorkItemBehavior(object):

    def prepare(self):
        notify(ActivityPrepared(self))
        self._create_workitem()

    def _create_workitem(self):
        """Used for activity in start and in event in prepare method.
        """
        workitems = {}
        if self.definition.applications:
            i = 0
            for application, formal, actual in self.definition.applications:
                factoryname = self.process.id + '.' + application
                workitem = createObject(factoryname, self)
                i += 1
                workitem.id = i
                workitems[i] = workitem, application, formal, actual

        self.workitems = workitems
        # Indexes workitems
        for wi in self.workitems.values():
            notify(ObjectAddedEvent(wi[0]))

    def _clear_workitem(self):
        """Used only by event in stop method.
        """
        for wi in self.workitems.values():
            wi[0].remove()
        self.workitems.clear()

    def start(self, transition):
        self._define_next_replay_node()
        notify(ActivityStarted(self))

        if self.workitems:
            if not hasattr(self.process, '_v_toreplay_app'):
                return
            replay_app = self.process._v_toreplay_app
            for workitem, app, formal, actual in self.workitems.values():
                if app == replay_app:
                    delattr(self.process, '_v_toreplay_app')
                    args = []
                    for parameter, name in zip(formal, actual):
                        if parameter.input:
                            args.append(
                                getattr(self.process.workflowRelevantData, name))
                            delattr(self.process.workflowRelevantData, name)
                    # If form.wi is a start workitem, replace it with real one.
                    if args:
                        if isinstance(args[0], WizardStep):
                            form = args[0].parent
                        else:
                            form = args[0]

                        # form.wi can be a StartWorkItem or DecisionWorkItem
                        # replace it with the real workitem
                        form.wi = workitem
                    if hasattr(self.process, '_v_toreplay_context'):
                        workitem.context = self.process._v_toreplay_context
                    workitem.start(*args)
        else:
            # Since we don't have any work items, we're done
            self._finish()

    def workItemFinished(self, work_item, *results):
        unused, app, formal, actual = self.workitems.pop(work_item.id)
        # The work_item is not in self.workitems but work_item.__parent__
        # is still referencing the node
        work_item.remove()
        # If work_item._p_oid is not set, it means we created and removed it
        # in the same transaction, so no need to mark the node as changed.
        if work_item._p_oid is None:
            self._p_changed = False
        else:
            self._p_changed = True
        res = results
        for parameter, name in zip(formal, actual):
            # Delete args before committing changes
            # We can't save a FileUpload field or a form instance...
            if parameter.input:
                try:
                    delattr(self.process.workflowRelevantData, name)
                except AttributeError:
                    pass
            if parameter.output:
                v = res[0]
                res = res[1:]
                setattr(self.process.workflowRelevantData, name, v)

        if res:
            raise TypeError("Too many results")

        notify(WorkItemFinished(
            work_item, app, actual, results))

        if not self.workitems:
            self._finish()


class EventHandler(FlowNode):
    def __init__(self, process, definition):
        super(EventHandler, self).__init__(process, definition)
        self.boundaryEvents = [defi.create(process)
                for defi in definition.boundaryEvents]


class EventHandlerDefinition(FlowNodeDefinition):
    factory = EventHandler
    boundaryEvents = ()


class AlreadyLocked(Exception):
    pass


class ProcessStarted:
    implements(IProcessStarted)

    def __init__(self, process):
        self.process = process

    def __repr__(self):
        return "ProcessStarted(%r)" % self.process


class ProcessFinished:
    implements(IProcessFinished)

    def __init__(self, process):
        self.process = process

    def __repr__(self):
        return "ProcessFinished(%r)" % self.process


class WorkItemFinished:

    def __init__(self, workitem, application, parameters, results):
        self.workitem =  workitem
        self.application = application
        self.parameters = parameters
        self.results = results

    def __repr__(self):
        return "WorkItemFinished(%r)" % self.application


class ActivityPrepared:

    def __init__(self, activity):
        self.activity = activity

    def __repr__(self):
        return "ActivityPrepared(%r)" % self.activity

class ActivityFinished:

    def __init__(self, activity):
        self.activity = activity

    def __repr__(self):
        return "ActivityFinished(%r)" % self.activity


class ActivityStarted:

    def __init__(self, activity):
        self.activity = activity

    def __repr__(self):
        return "ActivityStarted(%r)" % self.activity


class InvalidProcessDefinition(Exception):
    """A process definition isn't valid in some way.
    """


class ProcessError(Exception):
    """An error occurred in execution of a process.
    """

@grok.subscribe(ActivityPrepared)
@grok.subscribe(ActivityStarted)
@grok.subscribe(ActivityFinished)
def activity_handler(event):
    log.info('%s %s', thread.get_ident(), event)


def get_current_process_uid(request):
    p_uid = request.form.get('p_uid', None)
#    if p_uid is not None:
#        request.response.setCookie('p_uid', p_uid)
#    else:
#        p_uid = request.cookies.get('p_uid', None)
    return p_uid
# TODO expire cookie when a form action succeeded
#    request.response.expireCookie('p_uid')
#    set the cookie in the update() of a form only
