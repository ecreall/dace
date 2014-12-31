# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi
from pyramid.threadlocal import get_current_request

from dace.processinstance.core import  Behavior
from ...activity import (
    ElementaryAction, 
    LimitedCardinality, 
    InfiniteCardinality, 
    DataInput, 
    LoopActionCardinality, 
    LoopActionDataInput, 
    StartStep, 
    EndStep,
    ActionType)
from dace.objectofcollaboration.tests.example.objects import IObjectA
from dace.objectofcollaboration.principal.util import has_role


def relation_validationA(process, context):
    return True

def roles_validationA(process, context):
    return True

def processsecurity_validationA(process, context):
    return True

def state_validationA(process, context):
    return True



class ActionA(ElementaryAction):
    #identification et classification
    process_id = 'sample'
    node_id = 'a'
    title = 'action a'
    context = IObjectA
    #validation
    relation_validation = relation_validationA
    roles_validation = roles_validationA
    processsecurity_validation = processsecurity_validationA
    state_validation = state_validationA

    def start(self, context, request, appstruct, **kw):
        self.process.execution_context.add_created_entity('objecta', appstruct['object'])
        return {}


class ActionB(ElementaryAction):
    #identification et classification
    process_id = 'sample'
    node_id = 'b'
    title = 'action b'
    context = IObjectA
    processs_relation_id = 'objecta'
    #validation
    relation_validation = relation_validationA
    roles_validation = roles_validationA
    processsecurity_validation = processsecurity_validationA
    state_validation = state_validationA

    def start(self, context, request, appstruct, **kw):
        return {}


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

    def start(self, context, request, appstruct, **kw):
        if appstruct and 'object' in appstruct:
            self.process.execution_context.add_created_entity('systemobject', appstruct['object'])
            
        return {}

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
        return {}


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
        return {}

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
        return {}

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
        return {}

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


def conditionT(context, request):
    return True

class Step1(StartStep):
    behavior_id = 'step1'
    title = 'Etape 1 (A) '
    description = 'L\'etape 1 de l\'action Y'

    def start(self, context, request, appstruct, **kw):
        request.steps.append('step1')
        return {}

class Step2(Behavior):
    behavior_id = 'step2'
    title = 'Etape 2 (A) '
    description = 'L\'etape 2 de l\'action Y'

    def start(self, context, request, appstruct, **kw):
        request.steps.append('step2')
        return {}

class Step3(EndStep):
    behavior_id = 'step3'
    title = 'Etape 3 (A) '
    description = 'L\'etape 3 de l\'action Y'

    def start(self, context, request, appstruct, **kw):
        request.steps.append('step3')
        return {}

class ActionYSteps(ElementaryAction):
    steps = {'s1':Step1 , 's2':Step2 , 's3': Step3}
    transitions = (('s1', 's2', conditionT),('s2', 's3', conditionT))
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
        return {}


def system_roles_validation(process, context):
    return has_role(role=('System',))


class ActionSystem(ElementaryAction):
    #identification et classification
    process_id = 'sample'
    node_id = 'system'
    title = 'action system'
    context = IObjectA
    processs_relation_id = 'systemobject'
    actionType = ActionType.system
    #validation
    relation_validation = relation_validationA
    roles_validation = system_roles_validation
    processsecurity_validation = processsecurity_validationA
    state_validation = state_validationA

    def start(self, context, request, appstruct, **kw):

        return {}