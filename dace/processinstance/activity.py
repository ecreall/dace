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
        ValidationError)
from .lock import LockableElement
from dace.util import getBusinessAction, queryWorkItem
from dace.interfaces import (
    IProcessDefinition,
    IActivity,
    IBusinessAction)


ACTIONSTEPID = '__actionstepid__'


class Activity(BehavioralFlowNode, EventHandler):
    implements(IActivity)


class SubProcess(Activity):

    def __init__(self, process, definition):
        super(SubProcess, self).__init__(process, definition)
        self.wi = None
        self.subProcess = None

    def start_subprocess(self):
        registry = get_current_registry()
        pd = registry.getUtility(
                IProcessDefinition,
                self.definition.processDefinition)
        proc = pd()
        runtime = find_service('runtime')
        proc.__name__ = self.definition.processDefinition
        runtime.addtoproperty('processes', proc)
        proc.attachedTo = self
        proc.start()
        self.subProcess = proc

        # unindex wi, but dont delete it
        self.wi.remove()


class ActionType:
    automatic = 1
    manual = 2


def getBusinessActionValidator(action_cls):

    class BusinessActionValidator(Validator):

        @classmethod
        def validate(cls, context, request, **kw):
            e = ValidationError()
            process = None
            if 'process' in kw:
                process = kw['process']
            #import pdb; pdb.set_trace()
            work_item = queryWorkItem(action_cls.process_id, action_cls.node_id, request, context)
            if work_item is None:
                raise e

            if not context.__provides__(action_cls.context):
                raise e

            if action_cls.relation_validation and not action_cls.relation_validation.im_func(process, context):
                raise e

            if action_cls.roles_validation and not action_cls.roles_validation.im_func(process, context):
                raise e

            if action_cls.processsecurity_validation and not action_cls.processsecurity_validation.im_func(process, context):
                raise e

            if action_cls.state_validation and not action_cls.state_validation.im_func(process, context):
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
    view_action =  NotImplemented
    report =  NotImplemented
    study =  NotImplemented
    actionType = NotImplemented #!!
    steps = {}
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

    @staticmethod
    def get_instance(cls, context, request, **kw):
        instance = getBusinessAction(cls.process_id, cls.node_id, cls.behavior_id, request, context)
        if instance is None:
            return None

        return instance[0]

    @staticmethod
    def get_validator(cls, **kw):
        return getBusinessActionValidator(cls)

    @property
    def process(self):
        return self.workitem.process

    @property
    def view_name(self):
        return self.view_action.__view_name__

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
        if self.is_locked(request) or self.isexecuted:
            return False

        args =  {'process':self.workitem.process}
        try:
            self.__class__.get_validator(self.__class__).validate(context, request,**args)
            return True
        except ValidationError:
            return False

    def before_execution(self, context, request, **kw):
        self.lock(request)
        self.workitem.lock(request)

    def start(self, context, request, appstruct, **kw):
        # il y a probablement un moyen plus simple en cherchant la methode par son nom dans self par exemple..
        if appstruct is not None and ACTIONSTEPID in appstruct:
            return self.steps[appstruct[ACTIONSTEPID]].im_func(self, context, request, appstruct)
        else:
            return True

    def execute(self, context, request, appstruct, **kw):
        pass

    def after_execution(self, context, request, **kw):
        self.unlock(request)
        # TODO self.workitem is a real workitem?
        self.workitem.node.finish_behavior(self.workitem)

    def redirect(self, context, request, **kw):
        pass


class ElementaryAction(BusinessAction):

    def execute(self, context, request, appstruct, **kw):
        isFinished = self.start(context, request, appstruct, **kw)
        if isFinished:
            self.isexecuted = True
            self.after_execution(context, request, **kw)
            self.redirect(context, request, **kw)


# Une loopAction ne peut etre une action avec des steps. Cela n'a pas de sens
class LoopActionCardinality(BusinessAction):

    loopMaximum = None
    loopCondition = None
    testBefore = False

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
        if self.testBefore:
            self._executeBefore(context, request, appstruct, **kw)
        else:
            self._executeAfter(context, request, appstruct, **kw)

        self.isexecuted = True
        self.after_execution(context, request, **kw)
        self.redirect(context, request, **kw)


class LoopActionDataInput(BusinessAction):

    loopDataInputRef = None

    def execute(self, context, request, appstruct, **kw):
        instances = self.loopDataInputRef.im_func(context, request, self.process, appstruct)
        for item in instances:
            if kw is not None:
                kw['item'] = item
            else:
                kw = {'item': item}
            self.start(context, request, appstruct, **kw)

        self.isexecuted = True
        self.after_execution(context, request)
        self.redirect(context, request, **kw)


class MultiInstanceAction(BusinessAction):
    loopCardinality = None
    isSequential = False


class LimitedCardinality(MultiInstanceAction):


    def __init__(self, workitem):
        super(LimitedCardinality, self).__init__(workitem)
        self.instances = PersistentList()
        self.numberOfInstances = self.loopCardinality.im_func(self.process, None)
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
        isFinished = self.start(context, request, appstruct, **kw)
        if isFinished:
            self.after_execution(context, request, **kw)
            self.redirect(context, request, **kw)


class DataInput(MultiInstanceAction):

    loopDataInputRef = None
    dataIsPrincipal = True

    def __init__(self, workitem):
        super(DataInput, self).__init__(workitem)
        self.instances = PersistentList()
        # loopDataInputRef renvoie une liste d'elements identifiables
        self.instances = self.loopDataInputRef.im_func(self.process, None)
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
        cls.view_action =  principalaction.view_action
        cls.report =  principalaction.report
        cls.study =  principalaction.study
        cls.actionType = principalaction.actionType
        cls.relation_validation = principalaction.relation_validation
        cls.roles_validation =  principalaction.roles_validation
        cls.processsecurity_validation = principalaction.processsecurity_validation
        cls.state_validation =  principalaction.state_validation

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
            kw['item'] = self.item
        else:
            kw = {'item': self.item}
        return self.principalaction.start(context, request, appstruct, **kw)

    def redirect(self, context, request, **kw):
        if kw is not None:
            kw['item'] = self.item
        else:
            kw = {'item': self.item}
        self.principalaction.redirect(context, request, **kw)

    def execute(self, context, request, appstruct, **kw):
        isFinished = self.start(context, request, appstruct, **kw)
        if isFinished :
            self.isexecuted = True
            self.principalaction.instances.remove(self.item)
            self.after_execution(context, request, **kw)
            self.redirect(context, request, **kw)


class ActionInstanceAsPrincipal(ActionInstance):

    def validate(self, context, request, **kw):
        return (context is self.item) and super(ActionInstanceAsPrincipal, self).validate(context, request, **kw)

# il faut ajouter le callAction dans BPMN 2.0 c'est CallActivity

# La question est comment faire pour les actions multiStep?
# Je pense que cela peut être géré dans l'action start de l'action. La fonction start se charge d'exécuter la bonne
# Step (voir la méthode start de la class BusinessAction (comportement par défaut en plutistep)).
# dans ce cas le nom du step doit être ajouté dans args comme paramètre de l'action: chaque step (Vue, généralement un form)
# demande à l'action de s'exécuter action.execut(...). Avant cela, la step rajoute dans le args une clef ACTIONSTEPID et sa valeur
# correspondant à la méthode qui doit être exécuté. Le code associé aux steps et le start ainsi que les vues seront générés.

# exemple:

#class Monaction(ElementaryAction):
#
#    steps = {'s1':s1,'s2':s2}
#
#
#    def s1(self, context, request, appstruct, args):
#        pass
#
#    def s2(self, context, request, appstruct, args):
#        pass
