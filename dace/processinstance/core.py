# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi

import datetime
import pytz
import threading

from persistent import Persistent
from persistent.list import PersistentList
from pyramid.threadlocal import get_current_registry
from pyramid.interfaces import ILocation
from pyramid.events import subscriber
from zope.interface import implementer

from substanced.util import get_oid

from dace.interfaces import IProcessStarted, IProcessFinished
from dace import log
from dace.interfaces import IBehavior
from dace.descriptors import (
    CompositeMultipleProperty,
    SharedUniqueProperty, SharedMultipleProperty)
from dace.processdefinition.core import Path
from dace.objectofcollaboration.entity import Entity
from .workitem import DecisionWorkItem, StartWorkItem, WorkItem


PROCESS_HISTORY_KEY = 'process_history'


class BPMNElement(Entity):
    def __init__(self, definition, **kwargs):
        super(BPMNElement,self).__init__(**kwargs)
        self.id = definition.id
        if not self.title:
            self.title = definition.title

        if not self.description:
            self.description = definition.description


@implementer(ILocation)
class FlowNode(BPMNElement):

    incoming = SharedMultipleProperty('incoming', 'target', False)
    outgoing = SharedMultipleProperty('outgoing', 'source', False)
    workitems = CompositeMultipleProperty('workitems', None, False)
    process = SharedUniqueProperty('process', 'nodes', False)

    def __init__(self, definition, **kwargs):
        super(FlowNode,self).__init__( definition, **kwargs)

    def prepare(self):
        registry = get_current_registry()
        registry.notify(ActivityPrepared(self))

    def __call__(self, transaction):
        self.start(transaction)

    def find_executable_paths(self, source_path, source):
        pass# pragma: no cover

    def start(self, transaction):
        raise NotImplementedError# pragma: no cover

    def play(self, transitions):
        registry = get_current_registry()
        registry.notify(ActivityFinished(self))
        self.process.play_transitions(self, transitions)

    def replay_path(self, decision, transaction):
        pass# pragma: no cover

    def stop(self):
        pass# pragma: no cover

    @property
    def definition(self):
        return self.process.definition[self.__name__]

    def __repr__(self):# pragma: no cover
        return "%s(%r)" % (
            self.__class__.__name__,
            self.id
            )


class MakerFlowNode(FlowNode):

    def __init__(self, definition, **kwargs):
        super(MakerFlowNode, self).__init__(definition, **kwargs)

    def decide(self, transaction):
        workitems = self._calculate_decisions(transaction)
        if not workitems:
            return

        for i, workitem in enumerate(workitems.values()):
            workitem.__name__ = i+1
            self.addtoproperty('workitems', workitem)

        for decision_workitem in workitems.values():
            node_to_execute = decision_workitem.node
            if hasattr(node_to_execute, 'prepare_for_execution'):
                node_to_execute.prepare_for_execution()

    def _calculate_decisions(self, transaction, transitions=None):
        global_transaction = transaction.get_global_transaction()
        workitems = {}
        if transitions is None:
            transitions = self.outgoing

        for transition in transitions:
            if transition.sync or transition.validate(self.process):
                node = transition.target
                initial_path = Path([transition])
                global_transaction.start_subtransaction(type='Find', 
                                                    path=initial_path, 
                                                    initiator=self)
                executable_paths = node.find_executable_paths(
                                            initial_path, self)
                for executable_path in executable_paths:
                    dwi = DecisionWorkItem(executable_path, 
                           self.process[executable_path.targets[0].__name__],
                           self)
                    if dwi.node.__name__ in workitems:
                        workitems[dwi.node.__name__].merge(dwi)
                    else:
                        workitems[dwi.node.__name__] = dwi

        return workitems

    def refresh_decisions(self, transaction, transitions):
        workitems = self._calculate_decisions(transaction, transitions)
        new_workitems = [wi for wi in workitems.values() \
                         if not (wi in self.workitems)]
        if not  new_workitems:
            return

        for decision_workitem in new_workitems:
            node_to_execute = self.process[decision_workitem.node.__name__]
            if hasattr(node_to_execute, 'prepare_for_execution'):
                node_to_execute.prepare_for_execution()

        len_workitems = len(self.workitems)
        for i, workitem in enumerate(new_workitems):
            workitem.__name__ = i+1+len_workitems
            self.addtoproperty('workitems', workitem)

    def get_allconcernedworkitems(self):
        allprocessworkitems = self.process.getAllWorkItems()
        result = [wi for wi in allprocessworkitems \
                 if isinstance(wi, DecisionWorkItem) and \
                    self in wi.concerned_nodes()]

        return result

    def replay_path(self, decision, transaction):
        allconcernedkitems = self.get_allconcernedworkitems()
        for wi in allconcernedkitems:
            if decision.path.is_segment(wi.path):
                decision = wi
                break

        if decision in allconcernedkitems:
            self.finish_decisions(decision)
        else:
            self.finish_decisions(None)

    def finish_decisions(self, work_item):
        pass


class BehavioralFlowNode(MakerFlowNode):

    def __init__(self, definition, **kwargs):
        super(BehavioralFlowNode, self).__init__(definition, **kwargs)

    def find_executable_paths(self, source_path, source):
        decision_path = source_path.clone()
        source_transaction = source_path.transaction.__parent__
        source_transaction.remove_subtransaction(source_path.transaction)
        yield decision_path

    def _get_workitem(self):
        workitems = [w for w in self.workitems if w.validate() and \
                     isinstance(w, WorkItem)]
        if workitems:
            return workitems[0]

        workitems = [w for w in self.process.getAllWorkItems(
                                              node_id=self.__name__) \
                     if w.validate()]
        if workitems:
            wi = workitems[0]
            if isinstance(wi, DecisionWorkItem):
                wi = wi.consume()
                if wi is not None:
                    self.addtoproperty('workitems', wi)

                return wi

        return None

    def prepare(self):
        paths = self.process.global_transaction.find_allsubpaths_for(
                                                       self, 'Replay')
        user_decision = None
        if paths:
            user_decision = paths[0].transaction.initiator

        registry = get_current_registry()
        registry.notify(ActivityPrepared(self))
        workitem = WorkItem(self)
        workitem.id = 1
        workitem.__name__ = str(1)
        self.addtoproperty('workitems', workitem)
        if user_decision is not None:
            actions = user_decision.actions
            workitem.set_actions(actions)
            if getattr(user_decision, 'dont_lock', False):
                user_decision.call(workitem)
        else:
            workitem._init_actions()

    def start(self, transaction):
        registry = get_current_registry()
        registry.notify(ActivityStarted(self))

    def finish_behavior(self, work_item):
        if work_item  and not isinstance(work_item, StartWorkItem):
            self.delfromproperty('workitems', work_item)

        registry = get_current_registry()
        registry.notify(WorkItemFinished(work_item))
        paths = self.process.global_transaction.find_allsubpaths_for(
                                                        self, 'Start')
        if paths:
            for path in set(paths):
                source_transaction = path.transaction.__parent__
                source_transaction.remove_subtransaction(path.transaction)

        self.decide(self.process.global_transaction)

    def finish_decisions(self, work_item):
        first_transitions = work_item.path._get_transitions_source(self)
        if work_item is not None :
            work_item.validations.append(self)
            if work_item.is_finished:
                work_item.__parent__.delfromproperty('workitems', work_item)

        # clear commun work items
        allconcernedworkitems = self.get_allconcernedworkitems()
        all_stoped_wis = []
        for cdecision in allconcernedworkitems:
            for f_t in first_transitions:
                if cdecision.path.contains_transition(f_t):
                    if not (cdecision in all_stoped_wis) and \
                            cdecision is not work_item:
                        all_stoped_wis.append(cdecision)
                        cdecision.validations.append(self)
                        if cdecision.is_finished or \
                           not cdecision.path.is_segment(work_item.path):
                            # don't cdecision.node.stop()
                            cdecision.__parent__.delfromproperty(
                                       'workitems', cdecision)

                    break

        if work_item is not None:
            start_transition = work_item.path._get_transitions_source(self)[0]
            self.process.play_transitions(self, [start_transition])
            paths = self.process.global_transaction.find_allsubpaths_by_source(
                                                                   self, 'Find')
            if paths:
                for path in set(paths):
                    if work_item.path.contains_transition(path.first[0]):
                        source_transaction = path.transaction.__parent__
                        source_transaction.remove_subtransaction(
                                                 path.transaction)


class Error(Exception):

    principalmessage = NotImplemented
    causes = NotImplemented
    solutions = NotImplemented
    type = NotImplemented
    template = NotImplemented

    def __init__(self, **kwargs):
        super(Error, self).__init__()
        if 'msg' in kwargs:
            self.principalmessage = kwargs['msg']

        if 'causes' in kwargs:
            self.causes = kwargs['causes']

        if 'solutions' in kwargs:
            self.solutions = kwargs['solutions']

        if 'type' in kwargs:
            self.type = kwargs['type']

        if 'template' in kwargs:
            self.template = kwargs['template']


class ValidationError(Error):
    principalmessage = u""
    causes = []
    solutions = []
    type = 'danger'
    template = 'templates/message.pt'


class ExecutionError(Error):
    principalmessage = u""
    causes = []
    solutions = []
    type = 'danger'
    template = 'templates/message.pt'


class Validator(object):

    @classmethod
    def validate(cls, context, request, **kw):
        return True


class Step(object):

    def __init__(self, **kwargs):
        super(Step, self).__init__()
        self.wizard = None
        if 'wizard' in kwargs:
            self.wizard = kwargs['wizard']

        self.step_id = ''
        if 'step_id' in kwargs:
            self.step_id = kwargs['step_id']

        self._outgoing = PersistentList()
        self._incoming = PersistentList()

    def add_outgoing(self, transition):
        self._outgoing.append(transition)

    def add_incoming(self, transition):
        self._incoming.append(transition)


@implementer(IBehavior)
class Behavior(Step):

    title = NotImplemented
    description = NotImplemented
    behavior_id = NotImplemented

    def __init__(self, **kwargs):
        super(Behavior, self).__init__(**kwargs)
        if 'behavior_id' in kwargs:
            self.behavior_id = kwargs['behavior_id']

    @classmethod
    def get_instance(cls, context, request, **kw):
        instance = None
        if 'wizard' in kw and kw['wizard'] is not None:
            wizard = kw['wizard']
            _stepinstances = dict([(s.behavior_id, s) for s in  \
                                   list(dict(wizard.stepinstances).values())])
            instance = _stepinstances[cls.behavior_id]
        else:
            instance = cls()

        return instance  # raise ValidationError if no action

    @classmethod
    def get_validator(cls, **kw):
        return Validator  # defaultvalidator

    @property
    def _class_(self):
        """May be overrided later"""
        return self.__class__

    def validate(self, context, request, **kw):
        return True  # action instance validation

    def before_execution(self, context, request, **kw):
        pass  # pragma: no cover

    def start(self, context, request, appstruct, **kw):
        """Execution"""
        return {}

    def execute(self, context, request, appstruct, **kw):
        """Execution policy"""
        result_execution = {}
        try:
            result_execution = self.start(context, request, appstruct, **kw)
        except ExecutionError as error:
            self.after_execution(context, request, **kw)
            raise error

        kw.update(result_execution)
        self.after_execution(context, request, **kw)
        return self.redirect(context, request, **kw)

    def after_execution(self, context, request, **kw):
        pass  # pragma: no cover

    def cancel_execution(self, context, request, **kw):
        pass
        
    def redirect(self, context, request, **kw):
        pass  # pragma: no cover


def default_condition(context, request):
    return True


class Transition(Persistent):

    def __init__(self, 
                 source, 
                 target, 
                 id, 
                 condition=(lambda x, y:True), 
                 isdefault=False):
        self.wizard = source.wizard
        self.source = source
        self.target = target
        self.source.add_outgoing(self)
        self.target.add_incoming(self)
        self.condition = condition
        self.isdefault = isdefault
        self.id = id

    def validate(self, context, request, **args):
        return self.condition(context, request, **args)


class Wizard(Behavior):
    steps = {}
    transitions = ()

    def __init__(self, **kwargs):
        super(Wizard, self).__init__(**kwargs)
        self.transitionsinstances = PersistentList()
        self.stepinstances = PersistentList()
        for key, step in self.steps.items():
            stepinstance = step(step_id=key, wizard=self)
            self.stepinstances.append((stepinstance.step_id, stepinstance))

        _stepinstances = dict(self.stepinstances)
        for transition in self.transitions:
            sourceinstance = _stepinstances[transition[0]]
            targetinstance = _stepinstances[transition[1]]
            transitionid = transition[0]+'->'+transition[1]
            condition = None
            try:
                condition = transition[3]
            except Exception:
                condition = default_condition

            default = False
            try:
                default = transition[2]
            except Exception:
                pass

            transitioninstance = Transition(sourceinstance, targetinstance, 
                                            transitionid, condition, default)
            self.transitionsinstances.append((transitionid, transitioninstance))


class EventHandler(FlowNode):

    def __init__(self, definition, **kwargs):
        super(EventHandler, self).__init__(definition, **kwargs)
        self.boundaryEvents = []  # PersistentList()

    def _init_boundaryEvents(self, definition):
        self.boundaryEvents = [defi.create()
                for defi in definition.boundaryEvents]
        for bedef in definition.boundaryEvents:
            beinstance = bedef.create()
            beinstance.id = bedef.id
            beinstance.__name__ = bedef.__name__
            # FIXME: the implementation is unfinished
            self.process.addtoproperty('nodes', beinstance)

DEFAULTMAPPING_ACTIONS_VIEWS = {}

@implementer(IProcessStarted)
class ProcessStarted:

    def __init__(self, process):
        self.process = process

    def __repr__(self):# pragma: no cover
        return "ProcessStarted(%r)" % self.process


@implementer(IProcessFinished)
class ProcessFinished:

    def __init__(self, process):
        self.process = process

    def __repr__(self):# pragma: no cover
        return "ProcessFinished(%r)" % self.process


class WorkItemFinished:

    def __init__(self, workitem):
        self.workitem =  workitem

    def __repr__(self):# pragma: no cover
        return "WorkItemFinished(%r)" % self.node_id


class ActivityPrepared:

    def __init__(self, activity):
        self.activity = activity

    def __repr__(self):# pragma: no cover
        return "ActivityPrepared(%r)" % self.activity


class ActivityFinished:

    def __init__(self, activity):
        self.activity = activity

    def __repr__(self):# pragma: no cover
        return "ActivityFinished(%r)" % self.activity


class ActivityStarted:

    def __init__(self, activity):
        self.activity = activity

    def __repr__(self):# pragma: no cover
        return "ActivityStarted(%r)" % self.activity


class ActivityExecuted:

    def __init__(self, activity, contexts, user):
        self.activity = activity
        self.contexts = contexts
        self.user = user

    def __repr__(self):# pragma: no cover
        return "ActivityExecuted(%r)" % self.activity


class ProcessError(Exception):
    """An error occurred in execution of a process.
    """


@subscriber(ActivityPrepared)
@subscriber(ActivityStarted)
@subscriber(ActivityFinished)
def activity_handler(event):# pragma: no cover
    log.info('%s %s', threading.current_thread().ident, event)


@subscriber(ActivityExecuted)
def activity_executed__handler(event):
    now = datetime.datetime.now(tz=pytz.UTC)
    for context in event.contexts:
        if isinstance(context, Entity):
            process = event.activity.process
            node = event.activity.node
            node = {
                'date': now,
                'state': list(context.state),
                'user': get_oid(event.user, None),
                'activity_id': (event.activity.process_id,
                                event.activity.node_id),
                'activity_data': (getattr(process, 'title', None),
                                  getattr(node, 'title', None))
            }
            if not hasattr(context, 'annotations'):
                context.init_annotations()

            context.annotations.setdefault(
                PROCESS_HISTORY_KEY, PersistentList()).append(node)
