from persistent import Persistent
from pyramid.threadlocal import get_current_registry
from pyramid.interfaces import ILocation
from pyramid.events import subscriber
from zope.interface import implements, Attribute
from zope.component import createObject
from substanced.event import ObjectAdded
import thread

from dace.interfaces import IRuntime, IProcessStarted, IProcessFinished
from .workitem import DecisionWorkItem, StartWorkItem
from dace import log


#TODO
#class RuntimeNameChooser(NameChooser, grok.Adapter):
#    grok.context(IRuntime)
#    grok.implements(INameChooser)



class BPMNElement(object):
    def __init__(self, definition):
        self.id = definition.id

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
        registry = get_current_registry()
        registry.notify(ActivityPrepared(self))

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
        registry = get_current_registry()
        registry.notify(ActivityFinished(self))

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
        registry = get_current_registry()
        registry.notify(ActivityPrepared(self))
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
            registry = get_current_registry()
            registry.notify(ObjectAdded(wi[0]))

    def _clear_workitem(self):
        """Used only by event in stop method.
        """
        for wi in self.workitems.values():
            wi[0].remove()
        self.workitems.clear()

    def start(self, transition):
        self._define_next_replay_node()
        registry = get_current_registry()
        registry.notify(ActivityStarted(self))

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
                        # TODO WizardStep doesn't exist
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

        registry = get_current_registry()
        registry.notify(WorkItemFinished(
            work_item, app, actual, results))

        if not self.workitems:
            self._finish()


class EventHandler(FlowNode):
    def __init__(self, process, definition):
        super(EventHandler, self).__init__(process, definition)
        self.boundaryEvents = [defi.create(process)
                for defi in definition.boundaryEvents]



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


class ProcessError(Exception):
    """An error occurred in execution of a process.
    """


@subscriber(ActivityPrepared)
@subscriber(ActivityStarted)
@subscriber(ActivityFinished)
def activity_handler(event):
    log.info('%s %s', thread.get_ident(), event)
