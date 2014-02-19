# -*- coding: utf-8 -*-
from persistent import Persistent
from persistent.list import PersistentList
from pyramid.threadlocal import get_current_registry
from pyramid.threadlocal import get_current_request
from pyramid.interfaces import ILocation
from substanced.util import get_oid
from zope.interface import implements

from .core import EventHandler, WorkItemBehavior
from .lock import LockableElement

from .interfaces import (
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


#from zeam.form.base.interfaces import IForm


class ActionType:
    automatic = 1
    manual = 2


class BusinessAction(LockableElement, Persistent):
    implements(ILocation, IBusinessAction)
#    implements(IBusinessAction)

    context = NotImplemented
    action =  NotImplemented
    report =  NotImplemented
    study =  NotImplemented
    relation_validation = NotImplemented
    roles_validation = NotImplemented
    processsecurity_validation = NotImplemented
    state_validation = NotImplemented
    title = NotImplemented
    actionType = NotImplemented
    steps = {}

    def __init__(self, parent):
        super(BusinessAction, self).__init__()
        self.__parent__ = parent
        self.isexecuted = False

    @property
    def __name__(self):
        return self.action.__view_name__

    @property
    def process(self):
        return self.__parent__.process

    @property
    def view_name(self):
        return self.action.__view_name__

    @property
    def process_id(self):
        return self.__parent__.process_id

    @property
    def node_id(self):
        return self.__parent__.node_id

    @property
    def request(self):
        request = get_current_request()
        if self.process is not None:
            uid = get_oid(self.process)
            request.form[u'p_uid'] = uid
        return request

    def url(self, obj):
        if self.process is None:
            # TODO url
            return url(get_current_request(), obj, self.view_name)

        puid = get_oid(self.process)
        return url(get_current_request(), obj, self.view_name, {'p_uid': puid})

    def content(self, obj):
        content = u''
        registry = get_current_registry()
        view = registry.getMultiAdapter((obj, self.request), name=self.view_name)

        if not view.__providedBy__(IForm):
            return None

        view.update()
        content = (content + view.content() )
        return content

    def studyContent(self, obj):
        content = u''
        registry = get_current_registry()
        view = registry.getMultiAdapter((obj, self.request), name=self.study.__view_name__)

        if not view.__providedBy__(IForm):
            return None

        view.update()
        content = (content + view.content())
        return content

    def reportContent(self, obj):
        content = u''
        registry = get_current_registry()
        view = registry.getMultiAdapter((obj, self.request), name=self.report.__view_name__)

        if not view.__providedBy__(IForm):
            return None

        view.update()
        content = (content + view.content())
        return content

    def validate(self,obj):
        if  self.isexecuted and not obj.__provides__(self.context) or not self.__parent__.validate():
            return False

        if self.relation_validation and not self.relation_validation.im_func(self.process, obj):
            return False

        if self.roles_validation and not self.roles_validation.im_func(self.process, obj):
            return False

        if self.processsecurity_validation and not self.processsecurity_validation.im_func(self.process, obj):
            return False

        if self.state_validation and not self.state_validation.im_func(self.process, obj):
            return False

        return True

    def beforeexecution(self, request):
        self.lock(request)
        self.__parent__.lock(request)

    def start(self, context, request, appstruct, args=None):
        # il y a probablement un moyen plus simple en cherchant la methode par son nom dans self par exemple..
        if args is not None and ACTIONSTEPID in args:
            return self.steps[args[ACTIONSTEPID]].im_func(self, context, request, appstruct, args)
        else:
            return True

    def execute(self, context, request, appstruct, args = None):
        pass

    def afterexecution(self, request):
        self.unlock(request)
        self.__parent__.node.workItemFinished(self.__parent__)
        self.isexecuted = True

    def redirect(self, context, request, appstruct, args = None):
        pass


class ElementaryAction(BusinessAction):

    def execute(self, context, request, appstruct, args = None):
        isFinished = self.start(context, request, appstruct, args)
        if isFinished:
            self.afterexecution(request)
            self.redirect(context, request, appstruct, args)


# Une loopAction ne peut etre une action avec des steps. Cela n'a pas de sens
class LoopActionCardinality(BusinessAction):

    loopMaximum = None
    loopCondition = None
    testBefore = False

    def _executeBefore(self, context, request, appstruct, args=None):
        nbloop = 0
        while self.loopCondition.im_func(context, self.process, appstruct) and nbloop < self.loopMaximum:
            self.start(context, request, appstruct, args)
            nbloop += 1

    def _executeAfter(self, context, request, appstruct, args=None):
        nbloop = 0
        while nbloop < self.loopMaximum:
            self.start(context, request, appstruct, args)
            nbloop += 1
            if self.loopCondition.im_func(context, self.process, appstruct):
                break

    def execute(self, context, request, appstruct, args=None):
        if self.testBefore:
            self._executBefore(context, request, appstruct, args)
        else:
            self._executAfter(context, request, appstruct, args)

        self.afterexecution(request)
        self.redirect(context, request, appstruct, args)


class LoopActionDataInput(BusinessAction):

    loopDataInputRef = None

    def execute(self, context, request, appstruct, args=None):
        instances = self.loopDataInputRef.im_func(context, self.process, appstruct)
        for item in instances:
            if args is not None:
                args['item'] = item
            else:
                args = {'item': item}
            self.start(context, request, appstruct, args)

        self.afterexecution(request)
        self.redirect(context, request, appstruct, args)


class MultiInstanceActionLimitedCardinality(BusinessAction):

    loopCardinality = None
    isSequential = False

    def __init__(self, parent):
        super(MultiInstanceActionLimitedCardinality, self).__init__(parent)
        self.numberOfInstances = self.loopCardinality.im_func(None, self.process, None)
        for instance in range(self.numberOfInstances):
            self.__parent__.actions.append(ActionInstance(instance, self, parent))

        if self.numberOfInstances == 0:
            self.__parent__.node.workItemFinished(self.__parent__)

        self.isexecuted = True


class MultiInstanceActionInfiniteCardinality(BusinessAction):

    isSequential = False

    def beforeexecution(self, request):
        if self.isSequential:
            self.lock(request)
            self.__parent__.lock(request)

    def afterexecution(self, request):
        if self.isSequential:
            self.unlock(request)
            self.__parent__.unlock(request)

    def execute(self, context, request, appstruct, args=None):
        isFinished = self.start(context, request, appstruct, args)
        if isFinished:
            self.afterexecution(request)
            self.redirect(context, request, appstruct, args)


class MultiInstanceActionDataInput(BusinessAction):

    loopDataInputRef = None
    isSequential = False

    def __init__(self, parent):
        super(MultiInstanceActionDataInput, self).__init__(parent)
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

    # mia = multi instance action
    def __init__(self, item, mia, parent):
        super(ActionInstance, self).__init__(parent)
        self.mia = mia
        self.item = item

    def beforeexecution(self, request):
        self.lock(request)
        if self.mia.isSequential:
            self.__parent__.lock(request)

    def afterexecution(self, request):
        if self.mia.isSequential:
            self.__parent__.unlock(request)

        if  not self.mia.instances:
            self.__parent__.node.workItemFinished(self.__parent__)

        self.isexecuted = True

    def start(self, context, request, appstruct, args=None):
        if args is not None:
            args['item'] = self.item
        else:
            args = {'item': self.item}
        return self.mia.start(context, request, appstruct, args)

    def redirect(self, context, request, appstruct, args=None):
        if args is not None:
            args['item'] = self.item
        else:
            args = {'item': self.item}
        self.mia.redirect(context, request, appstruct, args)

    def execute(self, context, request, appstruct, args=None):
        isFinished = self.start(context, request, appstruct, args)
        if isFinished :
            self.mia.instances.pop(self.item)
            self.afterexecution(request)
            self.redirect(context, request, appstruct, args)


class ActionInstanceAsPrincipal(ActionInstance):

    def validate(self,obj):
        return (obj is self.item) and super(ActionInstanceAsPrincipal, self).validate(obj)


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
