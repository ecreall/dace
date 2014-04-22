# -*- coding: utf-8 -*-
from zope.interface import implements
from persistent import Persistent
from persistent.list import PersistentList

from pyramid.threadlocal import get_current_registry, get_current_request
from pyramid.interfaces import ILocation

from substanced.util import get_oid
from dace.util import find_service

from .core import (
        EventHandler,
        BehavioralFlowNode,
        Behavior,
        Validator,
        ValidationError,
        DEFAULTMAPPING_ACTIONS_VIEWS)
from .lock import LockableElement
from dace.util import getBusinessAction, queryWorkItem
from dace.interfaces import (
    IProcessDefinition,
    IActivity,
    IBusinessAction)

from .workitem import UserDecision


ITEM_INDEX = 'item'
ACTIONSTEPID = '__actionstepid__'


class Activity(BehavioralFlowNode, EventHandler):
    implements(IActivity)

    def __init__(self, definition):
        super(Activity, self).__init__(definition)

class SubProcess(Activity):

    def __init__(self, definition):
        super(SubProcess, self).__init__(definition)
        self.sub_processes = []

    def _start_subprocess(self):
        registry = get_current_registry()
        def_container = find_service('process_definition_container')
        pd = def_container.get_definition(self.definition.sub_process_definition.id)
        proc = pd()
        proc.__name__ = proc.id
        runtime = find_service('runtime')
        runtime.addtoproperty('processes', proc)
        proc.defineGraph(pd)
        proc.execute()
        self.sub_processes.append(proc)
        # unindex wi, but dont delete it
        #self.wi.remove()
        return proc


class ActionType:
    automatic = 1
    manual = 2


def getBusinessActionValidator(action_cls):

    class BusinessActionValidator(Validator):

        @classmethod
        def validate(cls, context, request, **kw):
            instance = action_cls.get_instance(context, request, **kw)
            if instance is None:
                e = ValidationError()
                raise e

            return True

    return BusinessActionValidator


class BusinessAction(LockableElement, Behavior,Persistent):
    implements(ILocation, IBusinessAction)

    #identification et classification
    groups = []
    process_id = NotImplemented
    node_id = NotImplemented
    #execution
    context = NotImplemented
    report =  NotImplemented
    study =  NotImplemented
    actionType = NotImplemented #!!
    #validation
    relation_validation = NotImplemented
    roles_validation = NotImplemented
    processsecurity_validation = NotImplemented
    state_validation = NotImplemented


    def __init__(self, workitem):
        super(BusinessAction, self).__init__()
        self.workitem = workitem
        self.isexecuted = False
        self.behavior_id = self.node_id
        self.sub_process = None

    @classmethod
    def get_instance(cls, context, request, **kw):
        instance = getBusinessAction(cls.process_id, cls.node_id, cls.behavior_id, request, context)
        if instance is None:
            return None

        return instance[0]

    @classmethod
    def get_allinstances(cls, context, request, **kw):
        instance = getBusinessAction(cls.process_id, cls.node_id, cls.behavior_id, request, context)
        if instance is None:
            return None

        return instance

    @classmethod
    def get_validator(cls, **kw):
        return getBusinessActionValidator(cls)

    @property
    def process(self):
        return self.workitem.process

    @property
    def node(self):
        return self.workitem.node

    @property
    def view_name(self):
        return self.action_view.__view_name__

    @property
    def request(self):
        request = get_current_request()
        if self.process is not None:
            uid = get_oid(self.process)
            request.params[u'p_uid'] = uid
        return request

    @property
    def isautomatic(self):
        if self.actionType is NotImplemented:
            return False
        elif self.actionType == ActionType.automatic:
            return True

        return False

    @property
    def action_view(self):
        if self.__class__ in DEFAULTMAPPING_ACTIONS_VIEWS:
            return DEFAULTMAPPING_ACTIONS_VIEWS[self.__class__]

        return None

    def url(self, obj):
        actionuid = get_oid(self.workitem)
        if self.process is None:
            # TODO url
            return get_current_request().mgmt_path(obj, self.view_name,  query={'action_uid':actionuid})

        return get_current_request().mgmt_path(obj, '@@'+self.view_name,  query={'action_uid':actionuid})

    def content(self, obj):
        content = u''
        # TODO url
        return content

    def studyContent(self, obj):
        content = u''
        # TODO url
        return content

    def reportContent(self, obj):
        content = u''
        # TODO url
        return content

    def validate(self, context, request, **kw):
        if self.isexecuted:
            return False

        if self.is_locked(request) or not self.workitem.validate():
            return False

        process = self.process
        if 'process' in kw:
            process = kw['process']

        if not context.__provides__(self.context):
            return False

        if self.relation_validation and not self.relation_validation.im_func(process, context):
            return False

        if self.roles_validation and not self.roles_validation.im_func(process, context):
            return False

        if self.processsecurity_validation and not self.processsecurity_validation.im_func(process, context):
            return False

        if self.state_validation and not self.state_validation.im_func(process, context):
            return False

        return True

    def before_execution(self, context, request, **kw):
        self.lock(request)
        self.workitem.lock(request)

    def start(self, context, request, appstruct, **kw):
        if kw is not None and ACTIONSTEPID in kw and hasattr(self, kw[ACTIONSTEPID]):
            step = getattr(self, kw[ACTIONSTEPID])
            return step(context, request, appstruct, **kw)
        else:
            return True

    def _consume_decision(self):
        if isinstance(self.workitem, UserDecision):
            self.workitem.consume()    

    def execute(self, context, request, appstruct, **kw):
        self._consume_decision()
        if isinstance(self.node, SubProcess) and self.sub_process is None:
            self.sub_process = self.node._start_subprocess()
            self.sub_process.attachedTo = self
            if ITEM_INDEX in kw:
                self.sub_process.execution_context.add_involved_entity(ITEM_INDEX, kw[ITEM_INDEX])

            self.process.execution_context.add_sub_execution_context(self.sub_process.execution_context)

    def finish_execution(self, context, request, **kw):
        self.after_execution(context, request, **kw)
        

    def after_execution(self, context, request, **kw):
        self.unlock(request)
        # TODO self.workitem is a real workitem?
        self.workitem.node.finish_behavior(self.workitem)



class ElementaryAction(BusinessAction):

    def execute(self, context, request, appstruct, **kw):
        super(ElementaryAction, self).execute(context, request, appstruct, **kw)
        isFinished = self.start(context, request, appstruct, **kw)
        if isFinished:
            self.isexecuted = True
            if self.sub_process is None:
                self.finish_execution(context, request, **kw)


# Une loopAction ne peut etre une action avec des steps. Cela n'a pas de sens
class LoopActionCardinality(BusinessAction):

    loopMaximum = None
    loopCondition = None
    testBefore = False

    def __init__(self, workitem):
        super(LoopActionCardinality, self).__init__(workitem)
        self.loopMaximum = self.loopMaximum.im_func(self.process)

    def _executeBefore(self, context, request, appstruct, **kw):
        nbloop = 0
        while self.loopCondition.im_func(context, request, self.process, appstruct) and nbloop < self.loopMaximum:
            self.start(context, request, appstruct, **kw)
            nbloop += 1

    def _executeAfter(self, context, request, appstruct, **kw):
        nbloop = 0
        while nbloop < self.loopMaximum:
            self.start(context, request, appstruct, **kw)
            nbloop += 1
            if not self.loopCondition.im_func(context, request, self.process, appstruct):
                break

    def execute(self, context, request, appstruct, **kw):
        super(LoopActionCardinality, self).execute(context, request, appstruct, **kw)
        if self.testBefore:
            self._executeBefore(context, request, appstruct, **kw)
        else:
            self._executeAfter(context, request, appstruct, **kw)

        self.isexecuted = True
        if self.sub_process is None:
            self.finish_execution(context, request, **kw)


class LoopActionDataInput(BusinessAction):

    loopDataInputRef = None

    def execute(self, context, request, appstruct, **kw):
        super(LoopActionDataInput, self).execute(context, request, appstruct, **kw)
        instances = self.loopDataInputRef.im_func(context, request, self.process, appstruct)
        for item in instances:
            if kw is not None:
                kw[ITEM_INDEX] = item
            else:
                kw = {ITEM_INDEX: item}
            self.start(context, request, appstruct, **kw)

        self.isexecuted = True
        if self.sub_process is None:
            self.finish_execution(context, request, **kw)


class MultiInstanceAction(BusinessAction):
    loopCardinality = None
    isSequential = False


class LimitedCardinality(MultiInstanceAction):


    def __init__(self, workitem):
        super(LimitedCardinality, self).__init__(workitem)
        self.instances = PersistentList()
        self.numberOfInstances = self.loopCardinality.im_func(self.process)
        for instance_num in range(self.numberOfInstances):
            #@TODO solution plus simple
            ActionInstance._init_attributes_(ActionInstance, self)
            instance = ActionInstance(instance_num, self, workitem)
            self.workitem.add_action(instance)
            self.instances.append(instance_num)

        self.isexecuted = True


class InfiniteCardinality(BusinessAction):

    loopCardinality = -1

    def before_execution(self, context, request, **kw):
        if self.isSequential:
            self.lock(request)
            self.workitem.lock(request)

    def after_execution(self, context, request, **kw):
        if self.isSequential:
            self.unlock(request)
            self.workitem.unlock(request)

    def execute(self, context, request, appstruct, **kw):
        super(InfiniteCardinality, self).execute(context, request, appstruct, **kw)
        self.start(context, request, appstruct, **kw)
        if self.sub_process is None:
            self.finish_execution(context, request, **kw)


class DataInput(MultiInstanceAction):

    loopDataInputRef = None
    dataIsPrincipal = True

    def __init__(self, workitem):
        super(DataInput, self).__init__(workitem)
        self.instances = PersistentList()
        # loopDataInputRef renvoie une liste d'elements identifiables
        self.instances = self.loopDataInputRef.im_func(self.process)
        for instance in self.instances:
            if self.dataIsPrincipal:
                ActionInstanceAsPrincipal._init_attributes_(ActionInstanceAsPrincipal, self)
                self.workitem.actions.append(ActionInstanceAsPrincipal(instance, self, workitem))
            else:
                ActionInstance._init_attributes_(ActionInstance, self)
                self.workitem.actions.append(ActionInstance(instance, self, workitem))

            self.isexecuted = True


class ActionInstance(BusinessAction):

    # principalaction = multi instance action
    def __init__(self, item, principalaction, workitem):
        super(ActionInstance, self).__init__(workitem)
        self.principalaction = principalaction
        self.item = item
        id = item
        if not isinstance(item, int):
            id  = get_oid(item)

        self.behavior_id = self.principalaction.node_id+'_'+str(id)

    @staticmethod
    def _init_attributes_(cls, principalaction):
        cls.process_id = principalaction.process_id
        cls.node_id = principalaction.node_id
        cls.context = principalaction.context
        cls.title = principalaction.title
        cls.actionType =  principalaction.actionType
        cls.report =  principalaction.report
        cls.study =  principalaction.study
        cls.relation_validation = principalaction.relation_validation
        cls.roles_validation =  principalaction.roles_validation
        cls.processsecurity_validation = principalaction.processsecurity_validation
        cls.state_validation =  principalaction.state_validation

    @property
    def action_view(self):
        if self.principalaction.__class__ in DEFAULTMAPPING_ACTIONS_VIEWS:
            return DEFAULTMAPPING_ACTIONS_VIEWS[self.principalaction.__class__]

        return None

    def before_execution(self,context, request, **kw):
        self.lock(request)
        if self.principalaction.isSequential:
            self.workitem.lock(request)

    def after_execution(self, context, request, **kw):
        self.unlock(request)
        if self.principalaction.isSequential:
            self.workitem.unlock(request)

        if  not self.principalaction.instances:
            self.workitem.node.finish_behavior(self.workitem)

    def start(self, context, request, appstruct, **kw):
        if kw is not None:
            kw[ITEM_INDEX] = self.item
        else:
            kw = {ITEM_INDEX: self.item}
        return self.principalaction.start(context, request, appstruct, **kw)

    def execute(self, context, request, appstruct, **kw):
        super(ActionInstance, self).execute(context, request, appstruct, **kw)
        isFinished = self.start(context, request, appstruct, **kw)
        if isFinished:
            self.isexecuted = True
            if self.sub_process is None:
                self.finish_execution(context, request, **kw)

    def finish_execution(self, context, request, **kw):
        self.principalaction.instances.remove(self.item)
        self.after_execution(context, request, **kw)


class ActionInstanceAsPrincipal(ActionInstance):

    def validate(self, context, request, **kw):
        return (context is self.item) and super(ActionInstanceAsPrincipal, self).validate(context, request, **kw)

    def execute(self, context, request, appstruct, **kw):
        if kw is not None:
            kw[ITEM_INDEX] = self.item
        else:
            kw = {ITEM_INDEX: self.item}
        super(ActionInstanceAsPrincipal, self).execute(context, request, appstruct, **kw)

# il faut ajouter le callAction dans BPMN 2.0 c'est CallActivity
