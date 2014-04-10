from pyramid.threadlocal import get_current_registry, get_current_request

from dace.util import utility
from dace.processinstance import workitem
from dace.processdefinition.processdef import ProcessDefinition
from dace.processdefinition.activitydef import ActivityDefinition
from dace.processdefinition.gatewaydef import GatewayDefinition
from dace.processdefinition.transitiondef import TransitionDefinition
from dace.interfaces import IProcessDefinition


class WorkItemX(workitem.WorkItem):
    def start(self):
        pass

@utility(name='sample.x')
class WorkItemFactoryX(workitem.WorkItemFactory):
    factory = WorkItemX

class WorkItemY(workitem.WorkItem):
    def start(self):
        pass

@utility(name='sample.y')
class WorkItemFactoryY(workitem.WorkItemFactory):
    factory = WorkItemY

class WorkItemZ(workitem.WorkItem):
    def start(self):
        pass

@utility(name='sample.z')
class WorkItemFactoryZ(workitem.WorkItemFactory):
    factory = WorkItemZ

####################################################

class WorkItemS(workitem.WorkItem):
    def start(self):
        self.node.execute()
        self.node.finish_behavior(self)

@utility(name='sample.s')
class WorkItemFactoryS(workitem.WorkItemFactory):
    factory = WorkItemS


class WorkItemA(workitem.WorkItem):
    def start(self):
        self.node.finish_behavior(self)

@utility(name='sample.a')
class WorkItemFactoryA(workitem.WorkItemFactory):
    factory = WorkItemA


class WorkItemD(workitem.WorkItem):
    def start(self):
        self.node.finish_behavior(self)

@utility(name ='sample.d')
class WorkItemFactoryD(workitem.WorkItemFactory):
    factory = WorkItemD


class WorkItemB(workitem.WorkItem):

    def start(self):
        # should not set a variable directly bu should use a output parameter
        self.node.process.workflowRelevantData.choice = "b"
        self.node.finish_behavior(self)

@utility(name ='sample.b')
class WorkItemFactoryB(workitem.WorkItemFactory):
    factory = WorkItemB


class WorkItemC(workitem.WorkItem):

    def start(self):
        self.node.finish_behavior(self)

@utility(name ='sample.c')
class WorkItemFactoryC(workitem.WorkItemFactory):
    factory = WorkItemC

class WorkItemEA(workitem.WorkItem):

    def start(self):
        self.node.finish_behavior(self)

@utility(name ='sample.ea')
class WorkItemFactoryEA(workitem.WorkItemFactory):
    factory = WorkItemEA

class WorkItemF(workitem.WorkItem):

    def start(self):
        self.node.finish_behavior(self)

@utility(name ='sample.f')
class WorkItemFactoryF(workitem.WorkItemFactory):
    factory = WorkItemF

class WorkItemAE(workitem.WorkItem):

    def start(self):
        self.node.finish_behavior(self)

@utility(name ='sample.ae')
class WorkItemFactoryAE(workitem.WorkItemFactory):
    factory = WorkItemAE


class WorkItemE(workitem.WorkItem):

    def start(self):
        self.node.execute()
        self.node.finish_behavior(self)

@utility(name ='sample.e')
class WorkItemFactoryE(workitem.WorkItemFactory):
    factory = WorkItemE


class WorkItemSc(workitem.WorkItem):

    def start(self):
        self.node.execute()
        self.node.finish_behavior(self)

@utility(name ='sample.sc')
class WorkItemFactorySc(workitem.WorkItemFactory):
    factory = WorkItemSc


class WorkItemSt(workitem.WorkItem):

    def start(self):
        self.node.execute()
        self.node.finish_behavior(self)

@utility(name ='sample.st')
class WorkItemFactorySt(workitem.WorkItemFactory):
    factory = WorkItemSt


class WorkItemCIE(workitem.WorkItem):

    def start(self):
        self.node.execute()
        self.node.finish_behavior(self)

@utility(name ='sample.cie')
class WorkItemFactoryCIE(workitem.WorkItemFactory):
    factory = WorkItemCIE


class WorkItemTIE(workitem.WorkItem):

    def start(self):
        self.node.execute()
        self.node.finish_behavior(self)

@utility(name ='sample.tie')
class WorkItemFactoryTIE(workitem.WorkItemFactory):
    factory = WorkItemTIE


class WorkItemD(workitem.WorkItem):

    def start(self):
        self.node.finish_behavior(self)


@utility(name ='sample.d')
class WorkItemFactoryD(workitem.WorkItemFactory):
    factory = WorkItemD

def relation_validationA(process, context):
    return True

def roles_validationA(process, context):
    return True

def processsecurity_validationA(process, context):
    return True

def state_validationA(process, context):
    return True

from ...activity import ElementaryAction, LimitedCardinality, InfiniteCardinality, DataInput, LoopActionCardinality, LoopActionDataInput
from dace.objectofcollaboration.tests.example.objects import IObjectA

class ActionX(ElementaryAction):
    #identification et classification
    groups = ['groupX']
    process_id = 'sample'
    node_id = 'x'
    context = IObjectA
    #validation
    relation_validation = relation_validationA
    roles_validation = roles_validationA
    processsecurity_validation = processsecurity_validationA
    state_validation = state_validationA

def cardB(process):
    return 3

class ActionY(LimitedCardinality):
    loopCardinality = cardB
    isSequential = True
    #identification et classification
    groups = ['groupY']
    process_id = 'sample'
    node_id = 'y'
    context = IObjectA
    #validation
    relation_validation = relation_validationA
    roles_validation = roles_validationA
    processsecurity_validation = processsecurity_validationA
    state_validation = state_validationA

class ActionYP(LimitedCardinality):
    loopCardinality = cardB
    isSequential = False
    #identification et classification
    groups = ['groupY']
    process_id = 'sample'
    node_id = 'y'
    context = IObjectA
    #validation
    relation_validation = relation_validationA
    roles_validation = roles_validationA
    processsecurity_validation = processsecurity_validationA
    state_validation = state_validationA

class ActionYPI(InfiniteCardinality):
    isSequential = False
    #identification et classification
    groups = ['groupY']
    process_id = 'sample'
    node_id = 'y'
    context = IObjectA
    #validation
    relation_validation = relation_validationA
    roles_validation = roles_validationA
    processsecurity_validation = processsecurity_validationA
    state_validation = state_validationA

class ActionYI(InfiniteCardinality):
    isSequential = True
    #identification et classification
    groups = ['groupY']
    process_id = 'sample'
    node_id = 'y'
    context = IObjectA
    #validation
    relation_validation = relation_validationA
    roles_validation = roles_validationA
    processsecurity_validation = processsecurity_validationA
    state_validation = state_validationA


def dataInputRef(process):
    request = get_current_request()
    return request.objects

class ActionYD(DataInput):
    loopDataInputRef = dataInputRef
    dataIsPrincipal = False
    isSequential = True
    #identification et classification
    groups = ['groupY']
    process_id = 'sample'
    node_id = 'y'
    context = IObjectA
    #validation
    relation_validation = relation_validationA
    roles_validation = roles_validationA
    processsecurity_validation = processsecurity_validationA
    state_validation = state_validationA

    def start(self, context, request, appstruct, **kw):
        item  = kw['item']
        item.is_executed = True  
        return True


class ActionYDp(DataInput):
    loopDataInputRef = dataInputRef
    dataIsPrincipal = True
    isSequential = True
    #identification et classification
    groups = ['groupY']
    process_id = 'sample'
    node_id = 'y'
    context = IObjectA
    #validation
    relation_validation = relation_validationA
    roles_validation = roles_validationA
    processsecurity_validation = processsecurity_validationA
    state_validation = state_validationA

    def start(self, context, request, appstruct, **kw):
        item  = kw['item']
        item.is_executed = True  
        return True

def loppdata(context, request, process, appstruct):
    return request.objects


class ActionYLD(LoopActionDataInput):
    loopDataInputRef = loppdata
    #identification et classification
    groups = ['groupY']
    process_id = 'sample'
    node_id = 'y'
    context = IObjectA
    #validation
    relation_validation = relation_validationA
    roles_validation = roles_validationA
    processsecurity_validation = processsecurity_validationA
    state_validation = state_validationA

    def start(self, context, request, appstruct, **kw):
        item  = kw['item']
        item.is_executed = True  
        return True

def loppcondition(context, request, process, appstruct):
    return request.bool

def loopmaximumc(process):
    return 10

class ActionYLC(LoopActionCardinality):

    loopMaximum = loopmaximumc
    loopCondition = loppcondition
    testBefore = False
    #identification et classification
    groups = ['groupY']
    process_id = 'sample'
    node_id = 'y'
    context = IObjectA
    #validation
    relation_validation = relation_validationA
    roles_validation = roles_validationA
    processsecurity_validation = processsecurity_validationA
    state_validation = state_validationA

    def start(self, context, request, appstruct, **kw):
        request.ylc = request.ylc+1  
        return True


class ActionZ(ElementaryAction):
    #identification et classification
    groups = ['groupZ']
    process_id = 'sample'
    node_id = 'z'
    context = IObjectA
    #validation
    relation_validation = relation_validationA
    roles_validation = roles_validationA
    processsecurity_validation = processsecurity_validationA
    state_validation = state_validationA
