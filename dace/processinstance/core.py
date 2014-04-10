from pyramid.threadlocal import get_current_registry
from pyramid.interfaces import ILocation
from pyramid.events import subscriber
from zope.component import createObject
from zope.interface import implements
import thread

from dace.interfaces import IProcessStarted, IProcessFinished
from .workitem import DecisionWorkItem
from dace import log
from dace.objectofcollaboration.object import Object, COMPOSITE_MULTIPLE, SHARED_MULTIPLE, SHARED_UNIQUE


class BPMNElement(object):
    def __init__(self, definition):
        self.id = definition.id


class FlowNode(BPMNElement, Object):
    implements(ILocation)

    properties_def = {'incoming': (SHARED_MULTIPLE, 'target', False),
                      'outgoing': (SHARED_MULTIPLE, 'source', False),
                      'workitems': (COMPOSITE_MULTIPLE, None, False),
                      'process': (SHARED_UNIQUE, 'nodes', False),
                      }

    def __init__(self, process, definition):
        BPMNElement.__init__(self, definition)
        Object.__init__(self)

    @property
    def workitems(self):
        return self.getproperty('workitems')

    @property
    def incoming(self):
        return self.getproperty('incoming')

    @property
    def outgoing(self):
        return self.getproperty('outgoing')

    @property
    def process(self):
        return self.getproperty('process')

    def prepare(self):
        registry = get_current_registry()
        registry.notify(ActivityPrepared(self))

    def __call__(self, transaction):
        self.start(transaction)

    def find_executable_paths(self, source_path, source):
        decision_path = source_path.clone()
        source_transaction = source_path.transaction.__parent__
        source_transaction.remove_subtransaction(source_path.transaction)
        yield decision_path

    def start(self, transaction):
        raise NotImplementedError

    def play(self, transitions):
        registry = get_current_registry()
        registry.notify(ActivityFinished(self))
        self.process.play_transitions(self, transitions)

    def replay_path(self, decision, transaction):
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

    def replay_path(self, decision, transaction):
        workitem = None
        if self.workitems:
            workitem = self.workitems[0]

        self.finish_behavior(workitem)

    def prepare(self):
        paths = self.process.global_transaction.find_allsubpaths_for(self, 'Replay')
        user_decision = None
        if paths:
            user_decision = paths[0].transaction.initiator

        registry = get_current_registry()
        registry.notify(ActivityPrepared(self))
        factoryname = self.definition.id
        workitem = createObject(factoryname, self)
        workitem.id = 1
        workitem.__name__ = str(1)
        self.addtoproperty('workitems', workitem)
        if user_decision is not None:
            actions = user_decision.actions
            workitem.set_actions(actions)
            if user_decision.dtlock:
                user_decision.call(workitem)
        else:
            workitem._init_actions()

    def start(self, transaction):
        registry = get_current_registry()
        registry.notify(ActivityStarted(self))

    def finish_behavior(self, work_item):
        if work_item is not None:
            self.delproperty('workitems', work_item)

        registry = get_current_registry()
        registry.notify(WorkItemFinished(work_item))
        paths = self.process.global_transaction.find_allsubpaths_for(self, 'Start')
        if paths:
            for p in set(paths):
                source_transaction = p.transaction.__parent__
                source_transaction.remove_subtransaction(p.transaction)

        if not self.workitems:
            allowed_transitions = []
            for transition in self.outgoing:
                if transition.sync or transition.condition(self.process):
                    allowed_transitions.append(transition)

            if allowed_transitions:
                self.play(allowed_transitions)


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

    behavior_id = NotImplemented
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
