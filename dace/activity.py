from grokcore.view.util import url
from persistent import Persistent
from zope.interface import implements
from zope.component import getUtility, getMultiAdapter
from zope.intid.interfaces import IIntIds
from zope.globalrequest import getRequest
from zope.location.interfaces import ILocation
from zope.container.interfaces import INameChooser

from .interfaces import IParameterDefinition, IProcessDefinition, IApplicationDefinition, IActivity, IBusinessAction, IRuntime
from .core import EventHandler, WorkItemBehavior


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

    def __init__(self, parent):
        super(BusinessAction, self).__init__()
        self.__parent__ = parent

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
        if not obj.__provides__(self.context) or not self.__parent__.validate():
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


    def execut(self, context, appstruct):
        pass


class LoopActionCardinality(BusinessAction):

    loopMaximum = None
    loopCondition = None
    testBefore = False

    def _executBefore(self, context, appstruct):
        nbloop = 0        
        while self.loopCondition.im_func(context, self.process, appstruct) and nbloop < loopMaximum:
            self.start(context, appstruct)
            nbloop += 1

    def _executAfter(self, context, appstruct):
        nbloop = 0        
        while nbloop < loopMaximum:
            self.start(context, appstruct)
            nbloop += 1
            if self.loopCondition.im_func(context, self.process, appstruct):
                break

    def execut(self, context, appstruct):
        if testBefore:
            self._executBefore(context, appstruct)
        else:
            self._executAfter(context, appstruct)

        self.__parent__.node.workItemFinished(self.__parent__)


class LoopActionDataInput(BusinessAction):

    loopDataInputRef = None

    def execut(self, context, appstruct):
        instances = self.loopDataInputRef.im_func(context, self.process, appstruct)       
        for item in instances:
            self.start(context, appstruct, item)
        self.__parent__.node.workItemFinished(self.__parent__)


class MultiInstanceActionCardinality(BusinessAction):
    
    loopCardinality = None
    isSequential = False 

    def __init__(self, parent):
        super(MultiInstanceActionCardinality, self).__init__(parent)
        self.numberOfInstances = 0
        self.numberOfTerminatedInstances = 0
        self.started = False

    def execut(self, context, appstruct):
        if isSequential:
            # bloquer le wi (== self.__parent__)

        if not self.started:
            self.started = True
            self.numberOfInstances = self.loopCardinality.im_func(context, self.process, appstruct)
        
        if self.numberOfTerminatedInstances <= self.numberOfInstances:
            self.start(context, appstruct)
            self.numberOfTerminatedInstances += 1

        if isSequential:
            # débloquer le wi
        
        if self.numberOfTerminatedInstances > self.numberOfInstances:
            self.__parent__.node.workItemFinished(self.__parent__)        


# il faut voir si nous pouvons travailler sur l'instanciation d el'action elle même.
# Dans ce cas il faut voir avec les autre actions.
class MultiInstanceActionDataInput(BusinessAction):

    loopDataInputRef = None
    isSequential = False
    dataIsPrincipal = False

    def __init__(self, parent):
        super(MultiInstanceActionCardinality, self).__init__(parent)
        self.started = False
        self.instances = []
        if dataIsPrincipal:
            # loopDataInputRef renvoie une liste d'elements identifiabls
            self.instances = self.loopDataInputRef.im_func(None, self.process, None)

    def _executasprincipal(self, context, appstruct):
        self.start(context, appstruct)
        self.instances.pop(self.instances.index(context))

    def _executasnotprincipal(self, context, appstruct):
        if not self.started:
            self.started = True
            self.instances = self.loopDataInputRef.im_func(context, self.process, appstruct)
        
        if self.instances:
            item = self.instances[0]
            self.start(context, appstruct, item)
            self.instances.pop(self.instances.index(item))

    def execut(self, context, appstruct):
        if isSequential:
            # bloquer le wi

        if dataIsPrincipal:
            self._executasprincipal(context, appstruct)
        else:
            self._executasnotprincipal(context, appstruct)

        if isSequential:
            # débloquer le wi
        
        if not self.instances:
            self.__parent__.node.workItemFinished(self.__parent__)

    def validate(self,obj):
        super(MultiInstanceActionDataInput, self).validate(obj)
        if dataIsPrincipal:
            if not (obj in self.instances):
                return False
            
        
