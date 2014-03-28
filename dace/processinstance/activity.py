# -*- coding: utf-8 -*-
from zope.interface import implements
from persistent import Persistent
from persistent.list import PersistentList

from pyramid.threadlocal import get_current_registry, get_current_request
from pyramid.interfaces import ILocation

from substanced.util import get_oid

from .core import (
        EventHandler,
        WorkItemBehavior,
        Behavior,
        Validator,
        ValidationError)
from .lock import LockableElement
from dace.util import getBusinessAction
from dace.interfaces import (
    IParameterDefinition,
    IProcessDefinition,
    IApplicationDefinition,
    IActivity,
    IBusinessAction,
    IRuntime)


ACTIONSTEPID = '__actionstepid__'


class Parameter(object):

    implements(IParameterDefinition)

    input = output = False

    def __init__(self, name):
        self.__name__ = name


class OutputParameter(Parameter):
    output = True


class InputParameter(Parameter):
    input = True


class InputOutputParameter(InputParameter, OutputParameter):
    pass


class Application:
    implements(IApplicationDefinition)

    def __init__(self, *parameters):
        self.parameters = parameters

    def defineParameters(self, *parameters):
        self.parameters += parameters

    def __repr__(self):
        input = u', '.join([param.__name__ for param in self.parameters
                           if param.input == True])
        output = u', '.join([param.__name__ for param in self.parameters
                           if param.output == True])
        return "<Application %r: (%s) --> (%s)>" %(self.id, input, output)


class Activity(WorkItemBehavior, EventHandler):
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
        runtime = registry.getUtility(IRuntime)
        # TODO Name chooser substanced
#        chooser = INameChooser(runtime)
        name = chooser.chooseName(self.definition.processDefinition, proc)
        runtime[name] = proc
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
        def validate(cls, context, request, args=None):
            instance = action_cls.get_instance(context, request, args)
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
     

    def __init__(self, parent):
        super(BusinessAction, self).__init__()
        self.__parent__ = parent
        self.isexecuted = False
        
    @staticmethod
    def get_instance(cls, context, request, args=None):
        instance = getBusinessAction(cls.process_id, cls.node_id, cls.behavior_id, request, context)
        if instance is None:
            return None

        return instance[0]

    @staticmethod
    def get_validator(cls):
        return getBusinessActionValidator(cls)

    @property
    def __name__(self):
        return self.view_action.__view_name__

    @property
    def process(self):
        return self.__parent__.process

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
        if actionType is NotImplemented:
            return False
        elif actionType == ActionType.automatic:
            return True

        return False

    def url(self, obj):
        actionuid = get_oid(self.parent) 
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

    def validate(self, context, request):
        if self.is_locked(request):
            return False

        if  self.isexecuted and not context.__provides__(self.context) or not self.__parent__.validate():
            return False

        if self.relation_validation and not self.relation_validation.im_func(self.process, context):
            return False

        if self.roles_validation and not self.roles_validation.im_func(self.process, context):
            return False

        if self.processsecurity_validation and not self.processsecurity_validation.im_func(self.process, context):
            return False

        if self.state_validation and not self.state_validation.im_func(self.process, context):
            return False

        return True

    def before_execution(self, context, request):
        self.lock(request)
        self.__parent__.lock(request)

    def start(self, context, request, appstruct):
        # il y a probablement un moyen plus simple en cherchant la methode par son nom dans self par exemple..
        if appstruct is not None and ACTIONSTEPID in appstruct:
            return self.steps[appstruct[ACTIONSTEPID]].im_func(self, context, request, appstruct)
        else:
            return True

    def execute(self, context, request, appstruct):
        pass

    def after_execution(self, context, request):
        self.unlock(request)
        self.__parent__.node.workItemFinished(self.__parent__)
        self.isexecuted = True

    def redirect(self, context, request, appstruct):
        pass


class ElementaryAction(BusinessAction):

    def execute(self, context, request, appstruct):
        isFinished = self.start(context, request, appstruct)
        if isFinished:
            self.afterexecution(request)
            self.redirect(context, request, appstruct)


# Une loopAction ne peut etre une action avec des steps. Cela n'a pas de sens
class LoopActionCardinality(BusinessAction):

    loopMaximum = None
    loopCondition = None
    testBefore = False

    def _executeBefore(self, context, request, appstruct):
        nbloop = 0
        while self.loopCondition.im_func(context, self.process, appstruct) and nbloop < self.loopMaximum:
            self.start(context, request, appstruct)
            nbloop += 1

    def _executeAfter(self, context, request, appstruct):
        nbloop = 0
        while nbloop < self.loopMaximum:
            self.start(context, request, appstruct)
            nbloop += 1
            if self.loopCondition.im_func(context, self.process, appstruct):
                break

    def execute(self, context, request, appstruct):
        if self.testBefore:
            self._executBefore(context, request, appstruct)
        else:
            self._executAfter(context, request, appstruct)

        self.after_execution(context, request)
        self.redirect(context, request, appstruct)


class LoopActionDataInput(BusinessAction):

    loopDataInputRef = None

    def execute(self, context, request, appstruct):
        instances = self.loopDataInputRef.im_func(context, self.process, appstruct)
        for item in instances:
            if appstruct is not None:
                appstruct['item'] = item
            else:
                appstruct = {'item': item}
            self.start(context, request, appstruct)

        self.after_execution(context, request)
        self.redirect(context, request, appstruct)


class MultiInstanceAction(BusinessAction):
    loopCardinality = None
    isSequential = False


class LimitedCardinality(MultiInstanceAction):


    def __init__(self, parent):
        super(LimitedCardinality, self).__init__(parent)
        self.numberOfInstances = self.loopCardinality.im_func(None, self.process, None)
        for instance in range(self.numberOfInstances):
            self.__parent__.actions.append(ActionInstance(instance, self, parent))

        if self.numberOfInstances == 0:
            self.__parent__.node.workItemFinished(self.__parent__)

        self.isexecuted = True


class InfiniteCardinality(BusinessAction):

    loopCardinality = -1

    def before_execution(self, context, request):
        if self.isSequential:
            self.lock(request)
            self.__parent__.lock(request)

    def after_execution(self, context, request):
        if self.isSequential:
            self.unlock(request)
            self.__parent__.unlock(request)

    def execute(self, context, request, appstruct):
        isFinished = self.start(context, request, appstruct)
        if isFinished:
            self.after_execution(context, request)
            self.redirect(context, request, appstruct)


class DataInput(MultiInstanceAction):

    loopDataInputRef = None
    dataIsPrincipal = True

    def __init__(self, parent):
        super(DataInput, self).__init__(parent)
        self.instances = PersistentList()
        # loopDataInputRef renvoie une liste d'elements identifiables
        self.instances = self.loopDataInputRef.im_func(None, self.process, None)
        for instance in self.instances:
            if self.dataIsPrincipal:
                self.__parent__.actions.append(ActionInstanceAsPrincipal(instance, self, parent))
            else:
                self.__parent__.actions.append(ActionInstance(instance, self, parent))

            self.isexecuted = True


class ActionInstance(BusinessAction):

    # principalaction = multi instance action
    def __init__(self, item, principalaction, parent):
        super(ActionInstance, self).__init__(parent)
        self.principalaction = principalaction
        self.item = item 
        self.actionid = self.actionid+'_'+str(get_oid(item))

    def before_execution(self,context, request):
        self.lock(request)
        if self.principalaction.isSequential:
            self.__parent__.lock(request)

    def after_execution(self, context, request):
        if self.principalaction.isSequential:
            self.__parent__.unlock(request)

        if  not self.principalaction.instances:
            self.__parent__.node.workItemFinished(self.__parent__)

        self.isexecuted = True

    def start(self, context, request, appstruct):
        if appstruct is not None:
            appstruct['item'] = self.item
        else:
            appstruct = {'item': self.item}
        return self.principalaction.start(context, request, appstruct)

    def redirect(self, context, request, appstruct):
        if appstruct is not None:
            appstruct['item'] = self.item
        else:
            appstruct = {'item': self.item}
        self.principalaction.redirect(context, request, appstruct)

    def execute(self, context, request, appstruct):
        isFinished = self.start(context, request, appstruct)
        if isFinished :
            self.principalaction.instances.pop(self.item)
            self.after_execution(context, request)
            self.redirect(context, request, appstruct)


class ActionInstanceAsPrincipal(ActionInstance):

    def validate(self, context, request):
        return (context is self.item) and super(ActionInstanceAsPrincipal, self).validate(context, request)

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
