from pyramid.threadlocal import get_current_registry, get_current_request

from dace.util import utility
from dace.processinstance import workitem
from dace.processdefinition.processdef import ProcessDefinition
from dace.processdefinition.activitydef import ActivityDefinition
from dace.processdefinition.gatewaydef import GatewayDefinition
from dace.processdefinition.transitiondef import TransitionDefinition
from dace.interfaces import IProcessDefinition

from substanced.content import content
from substanced.property import PropertySheet
from substanced.schema import NameSchemaNode
from substanced.util import renamer

from pontus.schema import Schema
from dace.objectofcollaboration.application import Application

from pontus.core import VisualisableElement, VisualisableElementSchema
from ...activity import ElementaryAction, LimitedCardinality, InfiniteCardinality, DataInput, LoopActionCardinality, LoopActionDataInput
from dace.objectofcollaboration.tests.example.objects import IObjectA


@content(
    'dace_root',
    )
class TestApplication(Application):
    name = renamer()

    def __init__(self, **kwargs):
        super(TestApplication, self).__init__(**kwargs)
        if not self.title:
            self.title = 'TestApplication'


def relation_validationA(process, context):
    return True

def roles_validationA(process, context):
    return True

def processsecurity_validationA(process, context):
    return True

def state_validationA(process, context):
    return True


def condition(obj):
    if not hasattr(obj, 'bool'):
        return True

    return obj.bool

class ActionX(ElementaryAction):
    #identification et classification
    groups = ['groupX']
    process_id = 'sample'
    node_id = 'x'
    title = 'action x'
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
    title = 'action y'
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
    title = 'action yp'
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
    title = 'action ypi'
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
    title = 'action yi'
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
    title = 'action yd'
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
    title = 'action ydp'
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
    title = 'action ylp'
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
    title = 'action ylc'
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
    title = 'action z'
    #validation
    relation_validation = relation_validationA
    roles_validation = roles_validationA
    processsecurity_validation = processsecurity_validationA
    state_validation = state_validationA

class ActionYSteps(ElementaryAction):
    #identification et classification
    groups = ['groupY']
    process_id = 'sample'
    node_id = 'y'
    context = IObjectA
    title = 'action ystep'
    #validation
    relation_validation = relation_validationA
    roles_validation = roles_validationA
    processsecurity_validation = processsecurity_validationA
    state_validation = state_validationA

    def step1(self, context, request, appstruct, **kw):
        request.steps.append('step1')  
        return False

    def step2(self, context, request, appstruct, **kw):
        request.steps.append('step2') 
        return False

    def step3(self, context, request, appstruct, **kw):
        request.steps.append('step3')  
        return True

class ActionSP(ElementaryAction):
    #identification et classification
    groups = ['groupSP']
    process_id = 'sample'
    node_id = 'sp'
    context = IObjectA
    title = 'action sp'
    #validation
    relation_validation = relation_validationA
    roles_validation = roles_validationA
    processsecurity_validation = processsecurity_validationA
    state_validation = state_validationA

class ActionSPMI(DataInput):
    loopDataInputRef = dataInputRef
    dataIsPrincipal = True
    isSequential = True
    #identification et classification
    groups = ['groupSP']
    process_id = 'sample'
    node_id = 'sp'
    context = IObjectA
    title = 'action spmi'
    #validation
    relation_validation = relation_validationA
    roles_validation = roles_validationA
    processsecurity_validation = processsecurity_validationA
    state_validation = state_validationA

    def start(self, context, request, appstruct, **kw):
        item  = kw['item']
        item.is_executed = True  
        return True
