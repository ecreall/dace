# -*- coding: utf-8 -*-
# Copyright (c) 2014 by Ecreall under licence AGPL terms
# avalaible on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi

from zope.interface import implementer
from persistent import Persistent
from persistent.list import PersistentList

from pyramid.threadlocal import get_current_request, get_current_registry
from pyramid.interfaces import ILocation

from substanced.event import ObjectModified
from substanced.util import get_oid

from dace.util import (
    find_service, get_obj, find_entities,
    getBusinessAction, getAllBusinessAction,
    getSite, request_memoize)
from dace import _
from .core import (
    EventHandler,
    BehavioralFlowNode,
    Wizard,
    Behavior,
    Validator,
    ValidationError,
    ExecutionError,
    DEFAULTMAPPING_ACTIONS_VIEWS,
    BPMNElement)
from .lock import LockableElement
from dace.interfaces import (
    IActivity,
    IBusinessAction)
from dace.objectofcollaboration.entity import ActionCall
from dace.objectofcollaboration.principal.util import get_current
from .workitem import UserDecision, StartWorkItem


def always_true(process, context):
    return True


MARKER_FUNC = always_true

ITEM_INDEX = 'item'

ACTIONSTEPID = '__actionstepid__'


class ActionType:
    automatic = 1
    manual = 2
    system = 3


def getBusinessActionValidator(action_cls):

    class BusinessActionValidator(Validator):

        @classmethod
        def validate(cls, context, request, **kw):
            instance = action_cls.get_instance(context, request, **kw)
            if instance is None:
                raise ValidationError()

            return True

    return BusinessActionValidator


@request_memoize
def validate_action(action, context, request, **kw):
    if not context.__provides__(action.context):
        return False, _('Context is not valid')

    process = kw.get('process', action.process)
    if not getattr(action.relation_validation,
                   '__func__', MARKER_FUNC)(process, context):
        return False, _('Context is not valid')

    if action.isexecuted:
        return False, _('Action is executed')

    if not action.workitem.validate():
        return False, _('Workitem is not valid')

    if getattr(action, 'isSequential', False) and action.is_locked(request):
        return False, _('Action is locked')

    elif not getattr(action.roles_validation,
                     '__func__', MARKER_FUNC)(process, context):
        return False, _('Role is not valid')

    if not getattr(action.processsecurity_validation,
                   '__func__', MARKER_FUNC)(process, context):
        return False, _('Security is violated')

    if not getattr(action.state_validation,
                   '__func__', MARKER_FUNC)(process, context):
        return False, _('Context state is not valid')

    _assigned_to = list(action.assigned_to)
    if _assigned_to:
        _assigned_to.append(getSite()['principals']['users']['admin'])
        current_user = get_current(request)
        if current_user not in _assigned_to:
            return False, _('Action is assigned to an other user')

    return True, _('Valid action')


@implementer(IActivity)
class Activity(BehavioralFlowNode, EventHandler):

    def __init__(self, definition):
        super(Activity, self).__init__(definition)
        self.assigned_to = PersistentList()

    def assigne_to(self, users):
        if not isinstance(users, (list, tuple)):
            users = [users]

        users = [u for u in users if not(u in self.assigned_to)]
        self.assigned_to.extend(users)

    def unassigne(self, users):
        if not isinstance(users, (list, tuple)):
            users = [users]

        users = [u for u in users if (u in self.assigned_to)]
        for user in users:
            self.assigned_to.remove(user)

    def set_assignment(self, users=None):
        self.assigned_to = PersistentList()
        if users is not None:
            self.assigne_to(users)


class SubProcess(Activity):

    def __init__(self, definition):
        super(SubProcess, self).__init__(definition)
        self.sub_processes = PersistentList()

    def _start_subprocess(self, action):
        def_container = find_service('process_definition_container')
        pd = def_container.get_definition(getattr(self.definition.sub_process_definition,
                                                  'id', self.definition.sub_process_definition))
        proc = pd()
        proc.__name__ = proc.id
        runtime = find_service('runtime')
        runtime.addtoproperty('processes', proc)
        proc.defineGraph(pd)
        self.definition._init_subprocess(self.process, proc)
        proc.attachedTo = action
        proc.execute()
        self.sub_processes.append(proc)
        return proc

    def stop(self):
        runtime = find_service('runtime')
        for process in self.sub_processes:
            process._finished = True
            for node in process.nodes:
                node.stop()
                node.setproperty('workitems', [])

            runtime.delfromproperty('processes', process)


@implementer(ILocation, IBusinessAction)
class BusinessAction(Wizard, LockableElement, Persistent):

    node_definition = NotImplemented
    context = NotImplemented
    processs_relation_id = NotImplemented
    actionType = NotImplemented
    #validation
    relation_validation = NotImplemented
    roles_validation = NotImplemented
    processsecurity_validation = NotImplemented
    state_validation = NotImplemented
    #style information
    access_controled = False

    def __init__(self, workitem, **kwargs):
        super(BusinessAction, self).__init__(**kwargs)
        self.workitem = workitem
        self.isexecuted = False
        self.behavior_id = self.node_id
        self.sub_process = None
        self.local_assigned_to = PersistentList()
        if self.title == '' or self.title is NotImplemented:
            self.title = self.node.title

        if self.description == '' or self.description is NotImplemented:
            self.description = self.node.description

    @classmethod
    def get_instance(cls, context, request, **kw):
        action_uid = request.params.get('action_uid', None)
        source_action = None
        if action_uid:
            source_action = get_obj(int(action_uid))

        if source_action and \
           source_action._class_ is cls and \
           source_action.validate(context, request):
            return source_action

        instances = getBusinessAction(context, request,
                                      cls.node_definition.process.id,
                                      cls.node_definition.__name__,
                                      cls.behavior_id,
                                      action_type=cls)

        if instances is None:
            return None

        isstart = request.params.get('isstart', False)
        if isstart:
            for inst in instances:
                if inst.isstart:
                    return inst

        return instances[0]

    @classmethod
    def get_allinstances(cls, context, request, **kw):
        instance = getBusinessAction(context, request,
                                      cls.node_definition.process.id,
                                      cls.node_definition.__name__,
                                      cls.behavior_id)
        return instance

    @classmethod
    def get_validator(cls, **kw):
        return getBusinessActionValidator(cls)

    @property
    def potential_contexts_ids(self):
        try:
            contexts = self.process.execution_context.involved_entities(
                                               self.processs_relation_id)
            result = []
            for context in contexts:
                try:
                    result.append(str(get_oid(context)))
                except Exception:
                    pass

            return result
        except Exception:
            return ['any']

    @property
    def actions(self):
        allactions = getAllBusinessAction(self)
        return [ActionCall(a, self) for a in allactions]

    @property
    def process(self):
        return self.workitem.process

    @property
    def node(self):
        return self.workitem.node

    @property
    def process_id(self):
        return self.workitem.process_id

    @property
    def definition(self):
        if self.node_definition is not NotImplemented:
            return self.node_definition

        return self.node.definition if isinstance(self.node, BPMNElement)\
               else self.node

    @property
    def node_id(self):
        return self.definition.__name__

    @property
    def groups(self):
        return self.definition.groups

    @property
    def view_name(self):
        return self.action_view.name

    @property
    def isautomatic(self):
        return self.actionType is ActionType.automatic

    @property
    def issystem(self):
        return self.actionType is ActionType.system

    @property
    def isstart(self):
        return isinstance(self.workitem, StartWorkItem)

    @property
    def informations(self):# pragma: no cover
        if self.process is not None:
            return 'Description: ' + \
                   self.description + \
                   '\n Process: '+self.process.title
        else:
            return 'Description: ' + \
                    self.description  + \
                    '\n Process: '+self.node.process.id

    @property
    def action_view(self):
        return DEFAULTMAPPING_ACTIONS_VIEWS.get(self.__class__, None)

    @property
    def assigned_to(self):
        if getattr(self, 'local_assigned_to', []):
            return self.local_assigned_to

        return getattr(self.node, 'assigned_to', [])

    def get_potential_context(self, request=None):
        if request is None:
            request = get_current_request()

        entities = []
        try:
            entities = [self.process.execution_context.involved_entity(
                        self.processs_relation_id)]
        except Exception:
            try:
                entities = self.process.execution_context.involved_collection(
                    self.processs_relation_id)
            except Exception:
                entities = find_entities((self.context,))

        for entity in entities:
            try:
                if entity:
                    self.validate(entity, request)
                    return entity

            except ValidationError:
                continue

        return None

    def url(self, obj):
        query = {}
        try:
            actionuid = get_oid(self)
            query = {'action_uid': actionuid}
        except AttributeError:
            query = {'isstart': 'True'}

        return get_current_request().resource_url(
            obj, '@@'+self.view_name,  query=query)

    def assigne_to(self, users):
        if not isinstance(users, (list, tuple)):
            users = [users]

        users = [u for u in users if u not in self.local_assigned_to]
        self.local_assigned_to.extend(users)

    def unassigne(self, users):
        if not isinstance(users, (list, tuple)):
            users = [users]

        users = [u for u in users if u in self.local_assigned_to]
        for user in users:
            self.local_assigned_to.remove(user)

    def set_assignment(self, users=None):
        self.local_assigned_to = PersistentList()
        if users is not None:
            self.assigne_to(users)

    def validate(self, context, request, **kw):
        is_valid, message = self.validate_mini(context, request, **kw)
        if not is_valid:
            raise ValidationError(msg=message)

        return True

    def validate_mini(self, context, request, **kw):
        return validate_action(self, context, request, **kw)

    def before_execution(self, context, request, **kw):
        self.lock(request)
        self.workitem.lock(request)

    def _consume_decision(self):
        if isinstance(self.workitem, UserDecision):
            self.workitem.consume()

    def start(self, context, request, appstruct, **kw):
        return {}

    def execute(self, context, request, appstruct, **kw):
        self._consume_decision()
        if self.isstart:
            return

        if isinstance(self.node, SubProcess) and not self.sub_process:
            self.sub_process = self.node._start_subprocess(self)
            if self.sub_process:
                if ITEM_INDEX in kw:
                    self.sub_process.execution_context.add_involved_entity(
                                                 ITEM_INDEX, kw[ITEM_INDEX])

                self.process.execution_context.add_sub_execution_context(
                                       self.sub_process.execution_context)

    def finish_execution(self, context, request, **kw):
        self.after_execution(context, request, **kw)

    def after_execution(self, context, request, **kw):
        self.unlock(request)
        self.workitem.unlock(request)
        # TODO self.workitem is a real workitem?
        if self.isexecuted:
            self.workitem.node.finish_behavior(self.workitem)

    def cancel_execution(self, context, request, **kw):
        self.unlock(request)
        self.workitem.unlock(request)

    def reindex(self):
        event = ObjectModified(self)
        registry = get_current_registry()
        registry.subscribers((event, self), None)


class StartStep(Behavior, Persistent):

    def __init__(self, **kwargs):
        super(StartStep, self).__init__(**kwargs)

    def execute(self, context, request, appstruct, **kw):
        BusinessAction.execute(self.wizard, context, request, appstruct, **kw)
        result_execution = {}
        try:
            result_execution = self.start(context, request, appstruct, **kw)
        except ExecutionError as error:
            self.after_execution(context, request, **kw)
            raise error

        kw.update(result_execution)
        self.after_execution(context, request, **kw)

class EndStep(Behavior, Persistent):

    def __init__(self, **kwargs):
        super(EndStep, self).__init__(**kwargs)

    def execute(self, context, request, appstruct, **kw):
        result_execution = {}
        try:
            result_execution = self.start(context, request, appstruct, **kw)
        except ExecutionError as error:
            self.after_execution(context, request, **kw)
            raise error

        kw.update(result_execution)
        self.wizard.isexecuted = True
        if self.wizard.sub_process is None:
            self.wizard.finish_execution(context, request, **kw)

        return self.redirect(context, request, **kw)

class ElementaryAction(BusinessAction):

    def execute(self, context, request, appstruct, **kw):
        super(ElementaryAction, self).execute(context, request, appstruct, **kw)
        result_execution = {}
        try:
            result_execution = self.start(context, request, appstruct, **kw)
        except ExecutionError as error:
            self.finish_execution(context, request, **kw)
            raise error

        kw.update(result_execution)
        self.isexecuted = True
        if not self.sub_process:
            self.finish_execution(context, request, **kw)

        return self.redirect(context, request, **kw)


# Une loopAction ne peut etre une action avec des steps. Cela n'a pas de sens
class LoopActionCardinality(BusinessAction):

    loopMaximum = None
    loopCondition = None
    testBefore = False

    def __init__(self, workitem, **kwargs):
        super(LoopActionCardinality, self).__init__(workitem, **kwargs)
        self.loopMaximum = self.loopMaximum.__func__(self.process)

    def _executeBefore(self, context, request, appstruct, **kw):
        nbloop = 0
        result_execution = {}
        while self.loopCondition.__func__(context, request,
                                    self.process, appstruct) and \
              nbloop < self.loopMaximum:
            result = self.start(context, request, appstruct, **kw)
            result_execution.update(result)
            nbloop += 1

        return result_execution

    def _executeAfter(self, context, request, appstruct, **kw):
        nbloop = 0
        result_execution = {}
        while nbloop < self.loopMaximum:
            result = self.start(context, request, appstruct, **kw)
            result_execution.update(result)
            nbloop += 1
            if not self.loopCondition.__func__(context, request,
                                        self.process, appstruct):
                break

        return result_execution

    def execute(self, context, request, appstruct, **kw):
        super(LoopActionCardinality, self).execute(context, request,
                                                   appstruct, **kw)
        result_execution = {}
        try:
            if self.testBefore:
                result_execution = self._executeBefore(
                                          context, request, appstruct, **kw)
            else:
                result_execution = self._executeAfter(
                                          context, request, appstruct, **kw)
        except ExecutionError as error:
            self.finish_execution(context, request, **kw)
            raise error

        kw.update(result_execution)
        self.isexecuted = True
        if self.sub_process is None:
            self.finish_execution(context, request, **kw)

        return self.redirect(context, request, **kw)


class LoopActionDataInput(BusinessAction):

    loopDataInputRef = None

    def execute(self, context, request, appstruct, **kw):
        super(LoopActionDataInput, self).execute(context, request,
                                                 appstruct, **kw)
        instances = self.loopDataInputRef.__func__(context, request,
                                             self.process, appstruct)
        result_execution = {}
        for item in instances:
            if kw:
                kw[ITEM_INDEX] = item
            else:
                kw = {ITEM_INDEX: item}

            result = self.start(context, request, appstruct, **kw)
            result_execution.update(result)

        kw.update(result_execution)
        self.isexecuted = True
        if self.sub_process is None:
            self.finish_execution(context, request, **kw)

        return self.redirect(context, request, **kw)


class MultiInstanceAction(BusinessAction):
    loopCardinality = None
    isSequential = False


    def is_locked(self, request):
        if not self.isSequential:
            return False

        return super(MultiInstanceAction, self).is_locked(request)


class LimitedCardinality(MultiInstanceAction):


    def __init__(self, workitem, **kwargs):
        super(LimitedCardinality, self).__init__(workitem, **kwargs)
        self.instances = PersistentList()
        self.numberOfInstances = self.loopCardinality.__func__(self.process)
        for instance_num in range(self.numberOfInstances):
            #@TODO solution plus simple
            ActionInstance._init_attributes_(ActionInstance, self)
            instance = ActionInstance(instance_num, self, workitem)
            self.workitem.add_action(instance)
            self.instances.append(instance_num)

        self.isexecuted = True


class InfiniteCardinality(MultiInstanceAction):

    loopCardinality = -1

    def before_execution(self, context, request, **kw):
        if self.isSequential:
            self.lock(request)
            self.workitem.lock(request)

    def after_execution(self, context, request, **kw):
        if self.isSequential:
            self.unlock(request)
            self.workitem.unlock(request)

    def cancel_execution(self, context, request, **kw):
        if self.isSequential:
            self.unlock(request)
            self.workitem.unlock(request)

    def execute(self, context, request, appstruct, **kw):
        super(InfiniteCardinality, self).execute(context, request,
                                                 appstruct, **kw)
        result_execution = self.start(context, request, appstruct, **kw)
        kw.update(result_execution)
        if self.sub_process is None:
            self.finish_execution(context, request, **kw)

        return self.redirect(context, request, **kw)


class DataInput(MultiInstanceAction):

    loopDataInputRef = None
    dataIsPrincipal = True

    def __init__(self, workitem, **kwargs):
        super(DataInput, self).__init__(workitem, **kwargs)
        self.instances = PersistentList()
        # loopDataInputRef renvoie une liste d'elements identifiables
        self.instances = self.loopDataInputRef.__func__(self.process)
        for instance in self.instances:
            if self.dataIsPrincipal:
                ActionInstanceAsPrincipal._init_attributes_(ActionInstanceAsPrincipal, self)
                self.workitem.actions.append(ActionInstanceAsPrincipal(
                                              instance, self, workitem))
            else:
                ActionInstance._init_attributes_(ActionInstance, self)
                self.workitem.actions.append(ActionInstance(
                                   instance, self, workitem))

            self.isexecuted = True


class ActionInstance(BusinessAction):

    # principalaction = multi instance action
    def __init__(self, item, principalaction, workitem, **kwargs):
        super(ActionInstance, self).__init__(workitem, **kwargs)
        self.principalaction = principalaction
        self.item = item
        item_id = item
        if not isinstance(item, int):
            item_id = get_oid(item)
            self.title = self.title+' ('+item.title+')'
        else:
            self.title = self.title+' ('+str(item)+')'

        self.behavior_id = self.principalaction.node_id+'_'+str(item_id)

    @property
    def _class_(self):
        return self.principalaction.__class__

    @staticmethod
    def _init_attributes_(cls, principalaction):
        cls.context = principalaction.context
        cls.node_definition = principalaction.node_definition
        cls.actionType = principalaction.actionType
        cls.relation_validation = principalaction.relation_validation
        cls.roles_validation = principalaction.roles_validation
        cls.processsecurity_validation = principalaction.processsecurity_validation
        cls.state_validation = principalaction.state_validation

    @property
    def action_view(self):
        if self.principalaction.__class__ in DEFAULTMAPPING_ACTIONS_VIEWS:
            return DEFAULTMAPPING_ACTIONS_VIEWS[self.principalaction.__class__]

        return None

    @property
    def informations(self):# pragma: no cover
        item_id = str(self.item)
        if not isinstance(self.item, int):
            item_id = self.item.title

        if self.process is not None:
            return 'Description: ' + \
                   self.description + \
                   '\n Process: ' + \
                   self.process.title+'\n Instance: '+item_id
        else:
            return 'Description: ' + \
                   self.description + \
                   '\n Process: ' + \
                   self.node.process.id+'\n Instance: '+item_id

    def before_execution(self,context, request, **kw):
        self.lock(request)
        if self.principalaction.isSequential:
            self.workitem.lock(request)

    def after_execution(self, context, request, **kw):
        self.unlock(request)
        if self.principalaction.isSequential:
            self.workitem.unlock(request)

        if not self.principalaction.instances:
            self.workitem.node.finish_behavior(self.workitem)

    def cancel_execution(self, context, request, **kw):
        self.unlock(request)
        if self.principalaction.isSequential:
            self.workitem.unlock(request)

    def start(self, context, request, appstruct, **kw):
        if kw:
            kw[ITEM_INDEX] = self.item
        else:
            kw = {ITEM_INDEX: self.item}
        return self.principalaction.start(context, request, appstruct, **kw)

    def execute(self, context, request, appstruct, **kw):
        super(ActionInstance, self).execute(context, request, appstruct, **kw)
        result_execution = {}
        try:
            result_execution = self.start(context, request, appstruct, **kw)
        except ExecutionError as error:
            self.unlock(request)
            if self.principalaction.isSequential:
                self.workitem.unlock(request)

            raise error

        kw.update(result_execution)
        self.isexecuted = True
        if self.sub_process is None:
            self.finish_execution(context, request, **kw)

        return self.principalaction.redirect(context, request, **kw)

    def finish_execution(self, context, request, **kw):
        self.principalaction.instances.remove(self.item)
        self.after_execution(context, request, **kw)


class ActionInstanceAsPrincipal(ActionInstance):

    def validate_mini(self, context, request, **kw):
        if context is not self.item:
            return False, _('Context not valid')

        return super(ActionInstanceAsPrincipal, self).validate_mini(
                                             context, request, **kw)

    def execute(self, context, request, appstruct, **kw):
        if kw is not None:
            kw[ITEM_INDEX] = self.item
        else:
            kw = {ITEM_INDEX: self.item}
        return super(ActionInstanceAsPrincipal, self).execute(
                             context, request, appstruct, **kw)

# il faut ajouter le callAction dans BPMN 2.0 c'est CallActivity
