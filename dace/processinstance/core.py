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
from dace.objectofcollaboration.object import Object, COMPOSITE_MULTIPLE


class BPMNElement(object):
    def __init__(self, definition):
        self.id = definition.id

class FlowNode(BPMNElement, Object):
    implements(ILocation)

    properties_def = {'workitems': (COMPOSITE_MULTIPLE, None, False)}

    @property
    def workitems(self):
        return self.getproperty('workitems')

    def __init__(self, process, definition):
        BPMNElement.__init__(self, definition)
        Object.__init__(self)
        self.process = process

    def prepare(self):
        registry = get_current_registry()
        registry.notify(ActivityPrepared(self))

    def __call__(self, transaction):
        self.start(transaction)

    def find_executable_paths(self, source_path, source):
        transition_path = [t for t in self.definition.incoming if t.source.id is source.id][0]
        source_path.add_transition(transition_path)
        yield source_path

    def start(self, transaction):
        raise NotImplementedError

    def play(self, transitions, transaction):
        registry = get_current_registry()
        registry.notify(ActivityFinished(self))
        self.process.play_transitions(self, transitions, transaction)

    def replay_path(self, path, transaction):
        pass

    def stop(self):
        pass

    @property
    def definition(self):
        return self.process.definition[self.__name__]


    def __repr__(self):
        return "%s(%r)" % (
            self.__class__.__name__,
            self.process.id + '.' +
            self.id
            )

class BehavioralFlowNode(object):


    def _get_workitem(self):
        if self.workitems:
            return self.workitems[0]

        workitems = self.process.getWorkItems()
        if self.id in workitems.keys():
            wi = workitems[self.id]
            if isinstance(wi, DecisionWorkItem):
                wi = wi.start()
                if wi is not None:
                    self.addtoproperty('workitems', wi)

                return wi

    def replay_path(self, path, transaction):
        workitem = None
        if self.workitems:
            workitem = self.workitems[0]

        self.finish_behavior(workitem, transaction)

    def prepare(self):
        registry = get_current_registry()
        registry.notify(ActivityPrepared(self))
        factoryname = self.definition.id
        workitem = createObject(factoryname, self)
        workitem.id = 1
        workitem.__name__ = str(1)
        self.addtoproperty('workitems', workitem)

    def start(self, transaction):
        registry = get_current_registry()
        registry.notify(ActivityStarted(self))
        paths = transaction.get_global_transaction().find_allsubpaths_for(self, 'Start')
        if paths:
            for p in paths:
                del p

    def finish_behavior(self, work_item, transaction):
        if work_item is not None:
	    self.delproperty('workitems', work_item)
            # If work_item._p_oid is not set, it means we created and removed it
            # in the same transaction, so no need to mark the node as changed.
            if work_item._p_oid is None:
                self._p_changed = False
            else:
                self._p_changed = True

        registry = get_current_registry()
        registry.notify(WorkItemFinished(work_item))
        if not self.workitems:
            allowed_transitions = []
            for transition in self.definition.outgoing:
                if transition.sync or transition.condition(self.process):
                    allowed_transitions.append(transition)

            self.play(allowed_transitions, transaction)

class ValidationError(Exception):
    principalmessage = u""
    causes = []
    solutions = []
    type = 'danger'
    template='templates/message.pt'


class Validator(object):

    @classmethod
    def validate(cls, context, request, **kw):
        return True


class Behavior(object):

    behaviorid = NotImplemented
    title = NotImplemented
    description = NotImplemented

    @classmethod
    def get_instance(cls, context, request, **kw):
        return cls() #raise ValidationError if no action

    @classmethod
    def get_validator(cls, **kw):
        return Validator #defaultvalidator

    def validate(self, context, request, **kw):
        return True #action instance validation

    def before_execution(self, context, request, **kw):
        pass

    def start(self, context, request, appstruct, **kw):
        pass

    def execute(self, context, request, appstruct, **kw):
        pass

    def after_execution(self, context, request, **kw):
        pass

    def redirect(self, context, request, **kw):
        pass




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

    def __init__(self, workitem):
        self.workitem =  workitem

    def __repr__(self):
        return "WorkItemFinished(%r)" % self.node_id


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
