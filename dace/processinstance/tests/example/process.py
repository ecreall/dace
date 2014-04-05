from pyramid.threadlocal import get_current_registry

from dace.util import utility
from dace.processinstance import workitem
from dace.processdefinition.processdef import ProcessDefinition
from dace.processdefinition.activitydef import ActivityDefinition
from dace.processdefinition.gatewaydef import GatewayDefinition
from dace.processdefinition.transitiondef import TransitionDefinition
from dace.interfaces import IProcessDefinition


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

    def start(self, layouts):
        self.node.finish_behavior(self, "c: %s" % layouts[0])

@utility(name ='sample.c')
class WorkItemFactoryC(workitem.WorkItemFactory):
    factory = WorkItemC


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
