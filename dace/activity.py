from grokcore.view.util import url
from persistent import Persistent
from zope.interface import implements
from zope.component import getUtility, getMultiAdapter
from zope.intid.interfaces import IIntIds
from zope.globalrequest import getRequest
from zope.location.interfaces import ILocation
from zope.container.interfaces import INameChooser

from .interfaces import IParameterDefinition, IProcessDefinition, IApplicationDefinition, IActivity, IAction, IRuntime
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


class Action(Persistent):
    implements(ILocation, IAction)

    context = NotImplemented
    action =  NotImplemented
    report =  NotImplemented
    study =  NotImplemented
    condition = NotImplemented
    title = NotImplemented
    actionType = NotImplemented

    def __init__(self, parent):
        super(Action, self).__init__()
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

#        url = view.url() + '/' + self.view_name

#        if self.process is not None:
#            intids = getUtility(IIntIds)
#            puid = intids.getId(self.process)
#            url = url + '?p_uid=' + str(puid)

        view.update()
        content = (content + view.content() )
#        content = re.sub('<form (.)* method', '<form action=\"'+url+'\" method', content)
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

    def validate(self, obj):                                                            # a enlever si l'indexation 'context-id' marche
        return obj.__provides__(self.context) and self.__parent__.validate() and self.condition.im_func(self.process, obj)

    def execut(self, wi, context, appstruct):
        pass


class LoopAction(Action):

    loopMaximum = None
    loopCondition = None
    testBefore = False
    

    def _executBefore(self, context, appstruct):
        nbloop = 0        
        while loopCondition(context, self.process, appstruct) and nbloop < loopMaximum:
            self.start(context, appstruct)
            nbloop += 1

    def _executAfter(self, context, appstruct):
        nbloop = 0        
        while nbloop < loopMaximum:
            self.start(context, appstruct)
            nbloop += 1
            if loopCondition(context, self.process, appstruct):
                break
            

    def execut(self, wi, context, appstruct):
        if testBefore:
            self._executBefore(context, appstruct)
        else:
            self._executAfter(context, appstruct)

        wi.node.workItemFinished(wi)


class MultiInstanceActionCardinality(Action):
    
    loopCardinality = None
    isSequential = False 

    def __init__(self, parent):
        super(MultiInstanceActionCardinality, self).__init__(parent)
        self.numberOfInstances = 0
        self.numberOfTerminatedInstances = 0
        self.started = False

    def execut(self, wi, context, appstruct):
        if isSequential:
            # bloquer le wi

        if not self.started:
            self.started = True
            self.numberOfInstances = loopCardinality(context, self.process, appstruct)
        
        if self.numberOfTerminatedInstances <= self.numberOfInstances:
            self.start(context, appstruct)
            self.numberOfTerminatedInstances += 1

        if isSequential:
            # débloquer le wi
        
        if self.numberOfTerminatedInstances > self.numberOfInstances:
            wi.node.workItemFinished(wi)        


# il faut voir si nous pouvons travailler sur l'instanciation d el'action elle même.
# Dans ce cas il faut voir avec les autre actions.
class MultiInstanceActionInstances(Action):

    loopDataInputRef = None
    isSequential = False 

    def __init__(self, parent):
        super(MultiInstanceActionCardinality, self).__init__(parent)
        self.started = False
        self.instances = []

    def execut(self, wi, context, appstruct):
        if isSequential:
            # bloquer le wi

        if not self.started:
            self.started = True
            self.instances = loopCardinality(context, self.process, appstruct)
        
        #self.start(context, appstruct)


        if isSequential:
            # débloquer le wi
        
        if self.numberOfTerminatedInstances > self.numberOfInstances:
            wi.node.workItemFinished(wi)


