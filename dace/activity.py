from grokcore.view.util import url
from persistent import Persistent
from zope.interface import implements
from zope.component import getUtility, getMultiAdapter
from zope.intid.interfaces import IIntIds
from zope.globalrequest import getRequest
from zope.location.interfaces import ILocation
from zope.container.interfaces import INameChooser
from datetime import datetime, timedelta
import pytz

from .interfaces import IParameterDefinition, IProcessDefinition, IApplicationDefinition, IActivity, IBusinessAction, IRuntime
from .core import EventHandler, WorkItemBehavior, AlreadyLocked


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
        pd = getUtility(
                IProcessDefinition,
                self.definition.processDefinition)
        proc = pd()
        runtime = getUtility(IRuntime)
        chooser = INameChooser(runtime)
        name = chooser.chooseName(self.definition.processDefinition, proc)
        runtime[name] = proc
        proc.attachedTo = self
        proc.start()
        self.subProcess = proc

        # unindex wi, but dont delete it
        self.wi.remove()


from zeam.form.base.interfaces import IForm


class ActionType:
    automatic = 1
    manual = 2


class BusinessAction(Persistent):
    implements(ILocation, IBusinessAction)

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
        request = getRequest()
        if self.process is not None:
            ids = getUtility(IIntIds)
            uid = ids.getId(self.process)
            request.form[u'p_uid'] = uid
        return request

    def url(self, obj):
        if self.process is None:
            return url(getRequest(), obj, self.view_name)

        intids = getUtility(IIntIds)
        puid = intids.getId(self.process)
        return url(getRequest(), obj, self.view_name, {'p_uid': puid})

    def content(self, obj):
        content = u''
        view = getMultiAdapter((obj, self.request), name=self.view_name)

        if not view.__providedBy__(IForm):
            return None

        view.update()
        content = (content + view.content() )
        return content

    def studyContent(self, obj):
        content = u''
        view = getMultiAdapter((obj, self.request), name=self.study.__view_name__)

        if not view.__providedBy__(IForm):
            return None

        view.update()
        content = (content + view.content())
        return content

    def reportContent(self, obj):
        content = u''
        view = getMultiAdapter((obj, self.request), name=self.report.__view_name__)

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

    def beforexecution(self, resuest):
        self.lock(resuest)
        self.__parent__.lock(request)

    def start(self, context, request, appstruct, args = None):
        # il y a probablement un moyen plus simple en cherchant la méthode par son nom dans self par exemple..
        return steps[appstruct['stepid']].im_func(self, context, request, appstruct, args)

    def execut(self, context, request, appstruct):
        pass

    def afterexecution(self, resuest):
        self.unlock(resuest)
        self.__parent__.node.workItemFinished(self.__parent__)
        self.isexecuted = True

    def redirect(self, context, request, appstruct):
        pass

    _lock = (None, None)

    def lock(self, request):
        """Raise AlreadyLocked if the activity was already locked by someone
        else.
        """
        if self.is_locked(request):
            raise AlreadyLocked(_(u"Already locked by ${user} at ${datetime}",
                mapping={'user': self._lock[0], 'datetime': self._lock[1]}))
        self._lock = (request.principal.id, datetime.now(pytz.utc))

    def unlock(self, request):
        """Raise AlreadyLocked if the activity was already locked by someone
        else.
        """
        if self.is_locked(request):
            raise AlreadyLocked(_(u"Already locked by ${user} at ${datetime}",
                mapping={'user': self._lock[0], 'datetime': self._lock[1]}))
        self._lock = (None, None)

    def is_locked(self, request):
        """If the activity was locked by the same user, return False.
        """
        if self._lock[1] is None:
            return False
        if self._lock[1] + LOCK_DURATION <= datetime.now(pytz.utc):
            return False
        if self._lock[0] == request.principal.id:
            return False
        return True


class ElementaryAction(BusinessAction):

    def execut(self, context, request, appstruct):
        isFinished = self.start(context, request, appstruct)
        if isFinished:
            self.afterexecution(request)
            self.redirect(context, request, appstruct)


# Une loopAction ne peut être une action avec des steps. Cela n'a pas de sens
class LoopActionCardinality(BusinessAction):

    loopMaximum = None
    loopCondition = None
    testBefore = False

    def _executBefore(self, context, request, appstruct):
        nbloop = 0       
        while self.loopCondition.im_func(context, self.process, appstruct) and nbloop < loopMaximum:
            self.start(context, request, appstruct)
            nbloop += 1

    def _executAfter(self, context, request, appstruct):
        nbloop = 0
        while nbloop < loopMaximum:
            self.start(context, request, appstruct)
            nbloop += 1
            if self.loopCondition.im_func(context, self.process, appstruct):
                break

    def execut(self, context, request, appstruct):
        if testBefore:
            self._executBefore(context, request, appstruct)
        else:
            self._executAfter(context, request, appstruct)

        self.afterexecution(request)
        self.redirect(context, request, appstruct)


class LoopActionDataInput(BusinessAction):

    loopDataInputRef = None

    def execut(self, context, request, appstruct):
        instances = self.loopDataInputRef.im_func(context, self.process, appstruct)  
        for item in instances:
            args = {'item': item}
            self.start(context, request, appstruct, args)

         self.afterexecution(request)
         self.redirect(context, request, appstruct)
        


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

    def beforexecution(self, resuest):
        if isSequential:
            self.lock(resuest)
            self.__parent__.lock(request)

    def afterexecution(self, resuest):
        if isSequential:
            self.unlock(resuest)
            self.__parent__.unlock(request)
 
    def execut(self, context, request, appstruct):
        isFinished = self.start(context, resuest, appstruct)
        if isFinished :
            self.afterexecution(request)
            self.redirect(context, request, appstruct)


class MultiInstanceActionDataInput(BusinessAction):

    loopDataInputRef = None
    isSequential = False

    def __init__(self, parent):
        super(MultiInstanceActionCardinality, self).__init__(parent)
        self.instances = PersistentList()
        # loopDataInputRef renvoie une liste d'éléments identifiables
        self.instances = self.loopDataInputRef.im_func(None, self.process, None)
        for instance in self.instances:
            if dataIsPrincipal:
                self.__parent__.actions.append(ActionInstanceAsPrincipal(instance, self, parent))
            else:
                self.__parent__.actions.append(ActionInstance(instance, self, parent))        

            self.isexecuted = True


class ActionInstance(BusinessAction):

    # mia = multi instance action
    def __init__(self, item, mia, parent)
        super(ActionInstance, self).__init__(parent)
        self.mia = mia
        self.item = item

    def beforexecution(self, resuest):
        self.lock(resuest)
        if self.mia.isSequential:
            self.__parent__.lock(request)

    def afterexecution(self, resuest):
        if self.mia.isSequential:
            self.__parent__.unlock(request)

        if  not self.mia.instances:
            self.__parent__.node.workItemFinished(self.__parent__)

        self.isexecuted = True            

    def start(self, context, resuest, appstruct, args = None):
        args = {'item': self.item}
        return self.mia.start(context, resuest, appstruct, args)

    def redirect(self, context, resuest, appstruct):
        args = {'item': self.item}
        self.mia.redirect(context, resuest, appstruct, args = None)
            
    def execut(self, context, resuest, appstruct):
        isFinished = self.start(context, resuest, appstruct)
        if isFinished :
            self.mia.instances.pop(self.item)
            self.afterexecution(request)
            self.redirect(context, request, appstruct)


class ActionInstanceAsPrincipal(ActionInstance):  

    def validate(self,obj):
        return (obj is self.item) and super(ActionInstanceAsPrincipal, self).validate(obj)



# La question est comment faire pour les actions multiStep?
# Je pense que cela peut être géré dans l'action start de l'action. La fonction start se charge d'exécuter la bonne
# Step (voir la méthode start de la class BusinessAction (comportement par défaut en plutistep)).
# dans ce cas le nom du step doit être ajouté dans le appstruct comme paramètre de l'action: chaque step (Vue, généralement un form) 
# demande à l'action de s'exécuter action.execut(...). Avant cela, la step rajoute dans le appstruct une clef 'stepid' et sa valeur 
# correspondant à la méthode qui doit être exécuté. Le code associé aux steps et le start ainsi que les vues seront générés.

# exemple:

#class Monaction(ElementaryAction):
#
#    steps = {'s1':s1,'s2':s2}
#
#    
#    def s1(self, contex, resuest, appstruct):
#        pass
#
#    def s2(self, contex, resuest, appstruct):
#        pass

 
