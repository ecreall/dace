from pyramid.threadlocal import get_current_registry
from pyramid.interfaces import ILocation
from pyramid.events import subscriber
from zope.component import createObject
from zope.interface import implements
import thread

from dace.interfaces import IProcessStarted, IProcessFinished
from .workitem import DecisionWorkItem, StartWorkItem, WorkItem
from dace import log
from dace.objectofcollaboration.object import Object, COMPOSITE_MULTIPLE, SHARED_MULTIPLE, SHARED_UNIQUE
from dace.processdefinition.core import Path

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

    def __init__(self, definition):
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
        pass

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
            self.id
            )

class MakerFlowNode(FlowNode):

    def __init__(self, definition):
        FlowNode.__init__(self, definition)

    def decide(self, transaction):
        workitems = self._calculate_decisions(transaction)
        if not workitems:
            return

        i = 0
        for workitem in workitems.values():
            i += 1
            workitem.__name__ = i
            self.addtoproperty('workitems', workitem)

        for decision_workitem in workitems.values():
            node_to_execute = decision_workitem.path.targets[0]
            if hasattr(node_to_execute, 'prepare_for_execution'):
                node_to_execute.prepare_for_execution()

    def _calculate_decisions(self, transaction, transitions=None):
        global_transaction = transaction.get_global_transaction()
        workitems = {}
        if transitions is None:
            transitions = self.outgoing

        for transition in transitions:
            if transition.sync or transition.condition(self.process):
                node = transition.target
                initial_path = Path([transition])
                subtransaction = global_transaction.start_subtransaction(type='Find', path=initial_path, initiator=self)
                executable_paths = node.find_executable_paths(initial_path, self)
                for executable_path in executable_paths:
                    dwi = DecisionWorkItem(executable_path, self.process[executable_path.targets[0].__name__])
                    if dwi.node.__name__ in workitems:
                        workitems[dwi.node.__name__].merge(dwi)
                    else:
                        workitems[dwi.node.__name__] = dwi

        return workitems

    def refresh_decisions(self, transaction, transitions):
        workitems = self._calculate_decisions(transaction, transitions)
        new_workitems = []
        for wi in workitems.values():
            if not (wi in self.workitems):
                new_workitems.append(wi)  
  
        if not  new_workitems:
            return
       
        for decision_workitem in new_workitems:
            node_to_execute = self.process[decision_workitem.path.targets[0].__name__]
            if hasattr(node_to_execute, 'prepare_for_execution'):
                node_to_execute.prepare_for_execution()

        i = len(self.workitems)
        for workitem in new_workitems:
            i += 1
            workitem.__name__ = i
            self.addtoproperty('workitems', workitem)

    def get_allconcernedworkitems(self):
        result = []
        allprocessworkitems = self.process.getAllWorkItems()
        for wi in allprocessworkitems:
            if isinstance(wi, DecisionWorkItem) and self in wi.concerned_nodes():
                result.append(wi)

        return result

    def replay_path(self, decision, transaction):
        allconcernedkitems = self.get_allconcernedworkitems()
        for wi in allconcernedkitems:
            if decision.path.is_segement(wi.path):
                decision = wi
                break

        if decision in allconcernedkitems:
            self.finish_decisions(decision)
        else:
            self.finish_decisions(None)

    def finish_decisions(self, work_item):
        pass


class BehavioralFlowNode(MakerFlowNode):

    def __init__(self, definition):
        MakerFlowNode.__init__(self, definition)

    def find_executable_paths(self, source_path, source):
        decision_path = source_path.clone()
        source_transaction = source_path.transaction.__parent__
        source_transaction.remove_subtransaction(source_path.transaction)
        yield decision_path

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
        if work_item is not None and not isinstance(work_item, StartWorkItem):
            self.delproperty('workitems', work_item)

        registry = get_current_registry()
        registry.notify(WorkItemFinished(work_item))
        paths = self.process.global_transaction.find_allsubpaths_for(self, 'Start')
        if paths:
            for p in set(paths):
                source_transaction = p.transaction.__parent__
                source_transaction.remove_subtransaction(p.transaction)

        self.decide(self.process.global_transaction)

    def finish_decisions(self, work_item):
        registry = get_current_registry()
        first_transition = work_item.path._get_transitions_source(self)
        if work_item is not None :
            work_item.validations.append(self)
            if work_item.is_finished:
                work_item.__parent__.delproperty('workitems', work_item)

        # clear commun work items
        allconcernedworkitems = self.get_allconcernedworkitems()
        all_stoped_wis = []
        for cdecision in allconcernedworkitems:
            for ft in first_transition:
                if cdecision.path.contains_transition(ft):
                    if not (cdecision in all_stoped_wis) and cdecision is not work_item:
                       all_stoped_wis.append(cdecision)
                       cdecision.validations.append(self)
                       if cdecision.is_finished or not cdecision.path.is_segement(work_item.path):
                           # don't cdecision.node.stop()
                           cdecision.__parent__.delproperty('workitems', cdecision)

                    break 

        if work_item is not None:
            start_transition = work_item.path._get_transitions_source(self)[0]
            self.process.play_transitions(self, [start_transition])

            paths = self.process.global_transaction.find_allsubpaths_by_source(self, 'Find')
            if paths:
                for p in set(paths):
                    if work_item.path.contains_transition(p.first[0]):
                        source_transaction = p.transaction.__parent__
                        source_transaction.remove_subtransaction(p.transaction)



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
    def __init__(self, definition):
        super(EventHandler, self).__init__( definition)
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
