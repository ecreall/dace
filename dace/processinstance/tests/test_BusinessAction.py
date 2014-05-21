from pyramid.threadlocal import get_current_registry

from dace.interfaces import IProcessDefinition
from dace.util import  getWorkItem, getBusinessAction
import dace.processinstance.tests.example.process as example
from dace.processdefinition.processdef import ProcessDefinition
from dace.processdefinition.activitydef import ActivityDefinition, SubProcessDefinition
from dace.processdefinition.gatewaydef import (
    ExclusiveGatewayDefinition, ParallelGatewayDefinition)
from dace.processdefinition.transitiondef import TransitionDefinition
from dace.processdefinition.eventdef import (
    StartEventDefinition,
    EndEventDefinition)

from dace.processinstance.tests.example.process import (
    ActionX,
    ActionY,
    ActionZ,
    ActionYP,
    ActionYPI,
    ActionYI,
    ActionYD,
    ActionYDp,
    ActionYLC,
    ActionYLD,
    ActionYSteps,
    ActionSP,
    ActionSPMI)
from dace.processinstance.workitem import StartWorkItem
from dace.objectofcollaboration.tests.example.objects import ObjectA
from dace.testing import FunctionalTests


class TestsBusinessAction(FunctionalTests):

    def tearDown(self):
        registry = get_current_registry()
        registry.unregisterUtility(provided=IProcessDefinition)
        super(TestsBusinessAction, self).tearDown()

    def _process_valid_actions(self):
        """
        S: start event
        E: end event
        G1,3(x): XOR Gateway
        P2,4(+): Parallel Gateway
        X, Y, Z: activities
                                       -----
                                    -->| X |------------\
                                   /   -----             \
    -----   ---------   --------- /                       \   ---------   -----
    | S |-->| G1(x) |-->| P2(+) |-                         -->| P4(+) |-->| E |
    -----   --------- \ --------- \    ---------   -----   /  ---------   -----
                       \           \-->| G3(x) |-->| Y |--/
                        \              /--------   -----
                         \    -----   /
                          \-->| Z |--/
                              -----
        """
        pd = ProcessDefinition(**{'id':u'sample'})
        self.app['sample'] = pd
        y = ActivityDefinition()
        pd.defineNodes(
                s = StartEventDefinition(),
                x = ActivityDefinition(contexts=[ActionX]),
                y = y,
                z = ActivityDefinition(contexts=[ActionZ]),
                g1 = ExclusiveGatewayDefinition(),
                g2 = ParallelGatewayDefinition(),
                g3 = ExclusiveGatewayDefinition(),
                g4 = ParallelGatewayDefinition(),
                e = EndEventDefinition(),
        )
        pd.defineTransitions(
                TransitionDefinition('s', 'g1'),
                TransitionDefinition('g1', 'g2'),
                TransitionDefinition('g1', 'z'),
                TransitionDefinition('g2', 'x'),
                TransitionDefinition('g2', 'g3'),
                TransitionDefinition('z', 'g3'),
                TransitionDefinition('g3', 'y'),
                TransitionDefinition('y', 'g4'),
                TransitionDefinition('x', 'g4'),
                TransitionDefinition('g4', 'e'),
        )

        self.config.scan(example)
        return y, pd

    def test_actions(self):
        y, pd = self._process_valid_actions()
        y._init_contexts([ActionY])
        self.def_container.add_definition(pd)
        start_wi = pd.start_process('x')
        actions_x = start_wi.actions
        self.assertEqual(len(actions_x), 1)
        action_x = actions_x[0]
        self.assertIs(action_x.workitem, start_wi)
        self.assertEqual(action_x.node_id, 'x')
        self.assertEqual(isinstance(action_x, ActionX), True)

        objecta= ObjectA()
        self.app['objecta'] = objecta
        call_actions = objecta.actions
        self.assertEqual(len(call_actions), 5)
        actions_id = [a.action.node_id for a in call_actions]
        self.assertIn('x', actions_id)
        self.assertIn('y', actions_id)
        self.assertIn('z', actions_id)
        actions_y = [a.action for a in call_actions if a.action.node_id == 'y']
        self.assertEqual(len(actions_y), 3)

        action_y = actions_y[0]
        action_y.before_execution(objecta, self.request)
        wi, proc = action_y.workitem.consume()
        wi.start_test_empty()
        action_y.execute(objecta, self.request, None, **{})
        self.assertIs(action_y.workitem, wi)
        actions_y_executed =  [a for a in actions_y if a.isexecuted]
        self.assertEqual(len(actions_y_executed), 1)
        self.assertIn(action_y, actions_y_executed)
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 2)
        self.assertIn('sample.x', workitems.keys())
        self.assertIn('sample.y', workitems.keys())
        actions_x = workitems['sample.x'].actions
        self.assertEqual(len(actions_x), 1)
        actions_y = workitems['sample.y'].actions
        self.assertEqual(len(actions_y), 4)# +1 pour l'action principale (3 pour les instances)
        actions_y_executed =  [a for a in actions_y if a.isexecuted]
        self.assertEqual(len(actions_y_executed), 2)# +1 pour l'action principale (1 pour les instances)
        actions_y_validated =  [a for a in actions_y if a.validate(objecta, self.request, **{})]
        self.assertEqual(len(actions_y_validated), 2)

        action_y = actions_y_validated[0]
        action_y.before_execution(objecta, self.request)# user == 'admin', lock action
        self.request.user = self.users['alice']# user == 'alice'
        actions_y_validated_alice =  [a for a in actions_y if a.validate(objecta, self.request, **{})]
        self.assertEqual(len(actions_y_validated_alice), 0)# ActionY is sequential

        self.request.user = self.users['admin']
        action_y.after_execution(objecta, self.request) # unlock action
        self.request.user = self.users['alice']# user == 'alice'
        actions_y_validated_alice =  [a for a in actions_y if a.validate(objecta, self.request, **{})]
        self.assertEqual(len(actions_y_validated_alice), 2)

        # get sample.y business action for alice
        allaction_y_alice = getBusinessAction('sample', 'y', None, self.request, objecta)
        self.assertEqual(len(allaction_y_alice), 5)# 2 pour actions_y_validated_alice et 3 pour le StartWorkItem Y (Une nouvelle execution)
        self.assertIn(actions_y_validated_alice[0], allaction_y_alice)
        self.assertIn(actions_y_validated_alice[1], allaction_y_alice)
        workitems_y_alice = []
        for a in allaction_y_alice:
            if a.workitem not in workitems_y_alice:
                workitems_y_alice.append(a.workitem)

        self.assertEqual(len(workitems_y_alice), 2)
        self.assertIn(workitems['sample.y'], workitems_y_alice)
        workitems_y_alice.remove(workitems['sample.y'])
        start_wi_y_alice = workitems_y_alice.pop()
        self.assertEqual(isinstance(start_wi_y_alice, StartWorkItem), True)
        self.assertEqual(len([a for a in allaction_y_alice if a.workitem is start_wi_y_alice]), 3)

        self.request.user = self.users['admin']
        for action in actions_y_validated:
            action.before_execution(objecta, self.request)
            action.execute(objecta, self.request, None, **{})

        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 1)
        self.assertIn('sample.x', workitems.keys())
        workitems['sample.x'].start_test_empty()
        actions_x[0].before_execution(objecta, self.request)
        actions_x[0].execute(objecta, self.request, None, **{})

        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 0)


    def test_actions_YParallel(self):
        y, pd = self._process_valid_actions()
        y._init_contexts([ActionYP])
        self.def_container.add_definition(pd)
        start_wi = pd.start_process('x')
        actions_x = start_wi.actions
        self.assertEqual(len(actions_x), 1)
        action_x = actions_x[0]
        self.assertIs(action_x.workitem, start_wi)
        self.assertEqual(action_x.node_id, 'x')
        self.assertEqual(isinstance(action_x, ActionX), True)

        objecta= ObjectA()
        self.app['objecta'] = objecta
        call_actions = objecta.actions
        self.assertEqual(len(call_actions), 5)
        actions_id = [a.action.node_id for a in call_actions]
        self.assertIn('x', actions_id)
        self.assertIn('y', actions_id)
        self.assertIn('z', actions_id)
        actions_y = [a.action for a in call_actions if a.action.node_id == 'y']
        self.assertEqual(len(actions_y), 3)

        action_y = actions_y[0]
        action_y.before_execution(objecta, self.request)
        wi, proc = action_y.workitem.consume()
        wi.start_test_empty()
        action_y.execute(objecta, self.request, None, **{})
        self.assertIs(action_y.workitem, wi)
        actions_y_executed =  [a for a in actions_y if a.isexecuted]
        self.assertEqual(len(actions_y_executed), 1)
        self.assertIn(action_y, actions_y_executed)


        actions_y_validated =  [a for a in actions_y if a.validate(objecta, self.request, **{})]
        self.assertEqual(len(actions_y_validated), 2)

        action_y = actions_y_validated[0]
        action_y.before_execution(objecta, self.request)# user == 'admin', lock action
        self.request.user = self.users['alice']# user == 'alice'
        actions_y_validated_alice =  [a for a in actions_y if a.validate(objecta, self.request, **{})]
        self.assertEqual(len(actions_y_validated_alice), 1)# ActionYP is parallel (1 action instance locked by admin)

        self.request.user = self.users['admin']
        action_y.after_execution(objecta, self.request) # unlock action
        self.request.user = self.users['alice']# user == 'alice'
        actions_y_validated_alice =  [a for a in actions_y if a.validate(objecta, self.request, **{})]
        self.assertEqual(len(actions_y_validated_alice), 2)

    def test_actions_YParallelI(self):
        y, pd = self._process_valid_actions()
        y._init_contexts([ActionYPI])
        self.def_container.add_definition(pd)
        start_wi = pd.start_process('x')
        actions_x = start_wi.actions
        self.assertEqual(len(actions_x), 1)
        action_x = actions_x[0]
        self.assertIs(action_x.workitem, start_wi)
        self.assertEqual(action_x.node_id, 'x')
        self.assertEqual(isinstance(action_x, ActionX), True)

        objecta= ObjectA()
        self.app['objecta'] = objecta
        call_actions = objecta.actions
        self.assertEqual(len(call_actions), 3)
        actions_id = [a.action.node_id for a in call_actions]
        self.assertIn('x', actions_id)
        self.assertIn('y', actions_id)
        self.assertIn('z', actions_id)
        actions_y = [a.action for a in call_actions if a.action.node_id == 'y']
        self.assertEqual(len(actions_y), 1) # InfiniteCardinality

        action_y = actions_y[0]
        action_y.before_execution(objecta, self.request)
        wi, proc = action_y.workitem.consume()
        wi.start_test_empty()
        action_y.execute(objecta, self.request, None, **{})
        self.assertIs(action_y.workitem, wi)

        actions_y_validated =  [a for a in actions_y if a.validate(objecta, self.request, **{})]
        self.assertEqual(len(actions_y_validated), 1)

        action_y = actions_y_validated[0]
        action_y.before_execution(objecta, self.request)# user == 'admin', lock action
        self.request.user = self.users['alice']# user == 'alice'
        actions_y_validated_alice =  [a for a in actions_y if a.validate(objecta, self.request, **{})]
        self.assertEqual(len(actions_y_validated_alice), 1)# ActionYPI is parallel (action instance is never locked)

        for x in range(10):
            action_y.before_execution(objecta, self.request)
            action_y.execute(objecta, self.request, None, **{})

        actions_y_validated_alice =  [a for a in actions_y if a.validate(objecta, self.request, **{})]
        self.assertEqual(len(actions_y_validated_alice), 1)

    def test_actions_YSequentialI(self):
        y, pd = self._process_valid_actions()
        y._init_contexts([ActionYI])
        self.def_container.add_definition(pd)
        start_wi = pd.start_process('x')
        actions_x = start_wi.actions
        self.assertEqual(len(actions_x), 1)
        action_x = actions_x[0]
        self.assertIs(action_x.workitem, start_wi)
        self.assertEqual(action_x.node_id, 'x')
        self.assertEqual(isinstance(action_x, ActionX), True)

        objecta= ObjectA()
        self.app['objecta'] = objecta
        call_actions = objecta.actions
        self.assertEqual(len(call_actions), 3)
        actions_id = [a.action.node_id for a in call_actions]
        self.assertIn('x', actions_id)
        self.assertIn('y', actions_id)
        self.assertIn('z', actions_id)
        actions_y = [a.action for a in call_actions if a.action.node_id == 'y']
        self.assertEqual(len(actions_y), 1) # InfiniteCardinality

        action_y = actions_y[0]
        action_y.before_execution(objecta, self.request)
        wi, proc = action_y.workitem.consume()
        wi.start_test_empty()
        action_y.execute(objecta, self.request, None, **{})
        self.assertIs(action_y.workitem, wi)

        actions_y_validated =  [a for a in actions_y if a.validate(objecta, self.request, **{})]
        self.assertEqual(len(actions_y_validated), 1)

        action_y = actions_y_validated[0]
        action_y.before_execution(objecta, self.request)# user == 'admin', lock action
        self.request.user = self.users['alice']# user == 'alice'
        actions_y_validated_alice =  [a for a in actions_y if a.validate(objecta, self.request, **{})]
        self.assertEqual(len(actions_y_validated_alice), 0)# ActionYPI is Sequential (action instance and workitem are locked)

        self.request.user = self.users['admin']
        for x in range(10):
            action_y.before_execution(objecta, self.request)
            action_y.execute(objecta, self.request, None, **{})

        actions_y_validated_alice =  [a for a in actions_y if a.validate(objecta, self.request, **{})]
        self.assertEqual(len(actions_y_validated_alice), 1)


    def test_actions_YSequentialD(self):
        y, pd = self._process_valid_actions()
        y._init_contexts([ActionYD]) # multi instance (pour chaque instance nous avons un objet)
        self.def_container.add_definition(pd)
        objecta= ObjectA()
        objecta.is_executed = False
        objectb= ObjectA()
        objectb.is_executed = False
        objectc= ObjectA()
        self.app['objecta'] = objecta
        self.app['objectb'] = objectb
        self.app['objectc'] = objectc

        self.request.objects = [objecta, objectb]
        start_wi = pd.start_process('x')
        actions_x = start_wi.actions
        self.assertEqual(len(actions_x), 1)
        action_x = actions_x[0]
        self.assertIs(action_x.workitem, start_wi)
        self.assertEqual(action_x.node_id, 'x')
        self.assertEqual(isinstance(action_x, ActionX), True)

        call_actions = objectc.actions
        self.assertEqual(len(call_actions), 4)
        actions_id = [a.action.node_id for a in call_actions]
        self.assertIn('x', actions_id)
        self.assertIn('y', actions_id)
        self.assertIn('z', actions_id)
        actions_y = [a.action for a in call_actions if a.action.node_id == 'y']
        self.assertEqual(len(actions_y), 2) # 1 instance pour objecta et une autre pour objectb

        actions_y_a = [a for a in actions_y if a.item is objecta]
        self.assertEqual(len(actions_y_a), 1)
        actions_y_b = [a for a in actions_y if a.item is objectb]
        self.assertEqual(len(actions_y_b), 1)
        action_a = actions_y_a[0]
        action_b = actions_y_b[0]
        action_a.before_execution(objectc, self.request)
        self.assertIs(action_a.workitem, action_b.workitem)

        wi, proc = action_a.workitem.consume()
        wi.start_test_empty()
        action_a.execute(objectc, self.request, None, **{})
        self.assertEqual(objecta.is_executed, True)
        self.assertEqual(objectb.is_executed, False)
        self.assertIs(action_a.workitem, wi)

        actions_y_validated =  [a for a in actions_y if a.validate(objectc, self.request, **{})]
        self.assertEqual(len(actions_y_validated), 1)
        self.assertIn(action_b, actions_y_validated)

        action_b.before_execution(objectc, self.request)# user == 'admin', lock action
        self.request.user = self.users['alice']# user == 'alice'
        actions_y_validated_alice =  [a for a in actions_y if a.validate(objecta, self.request, **{})]
        self.assertEqual(len(actions_y_validated_alice), 0)# ActionYD is Sequential (action instance and workitem are locked)

    def test_actions_YSequentialDp(self):
        y, pd = self._process_valid_actions()
        y._init_contexts([ActionYDp]) # multi instance (pour chaque instance nous avons un objet, l'objet est le context principal)
        self.def_container.add_definition(pd)
        objecta= ObjectA()
        objectb= ObjectA()
        objectc= ObjectA()
        self.app['objecta'] = objecta
        self.app['objectb'] = objectb
        self.app['objectc'] = objectc

        self.request.objects = [objecta, objectb]
        start_wi = pd.start_process('x')
        actions_x = start_wi.actions
        self.assertEqual(len(actions_x), 1)
        action_x = actions_x[0]
        self.assertIs(action_x.workitem, start_wi)
        self.assertEqual(action_x.node_id, 'x')
        self.assertEqual(isinstance(action_x, ActionX), True)

        call_actions = objectc.actions
        self.assertEqual(len(call_actions), 2)
        actions_id = [a.action.node_id for a in call_actions]
        self.assertIn('x', actions_id)
        self.assertIn('z', actions_id)

        call_actions = objecta.actions
        self.assertEqual(len(call_actions), 3)
        actions_id = [a.action.node_id for a in call_actions]
        self.assertIn('x', actions_id)
        self.assertIn('y', actions_id)
        self.assertIn('z', actions_id)
        actions_y = [a.action for a in call_actions if a.action.node_id == 'y']
        self.assertEqual(len(actions_y), 1) # 1 instance pour objecta et une autre pour objectb
        action_a = actions_y[0]

        call_actions = objectb.actions
        self.assertEqual(len(call_actions), 3)
        actions_id = [a.action.node_id for a in call_actions]
        self.assertIn('x', actions_id)
        self.assertIn('y', actions_id)
        self.assertIn('z', actions_id)
        actions_y = [a.action for a in call_actions if a.action.node_id == 'y']
        self.assertEqual(len(actions_y), 1) # 1 instance pour objecta et une autre pour objectb

        action_a.before_execution(objecta, self.request)
        action_a.execute(objecta, self.request, None, **{})
        proc = action_a.node.process
        actions_b = [a for a in action_a.workitem.actions if hasattr(a, 'item') and a.item is objectb]
        self.assertEqual(len(actions_b), 1)
        action_b = actions_b[0]
        action_b.before_execution(objectb, self.request)
        action_b.execute(objectb, self.request, None, **{})

        workitems = proc.getWorkItems()
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 1)
        self.assertIn('sample.x', nodes_workitems)

    def _test_actions_YLC(self, pd, y):
        start_wi = pd.start_process('x')
        actions_x = start_wi.actions
        self.assertEqual(len(actions_x), 1)
        action_x = actions_x[0]
        self.assertIs(action_x.workitem, start_wi)
        self.assertEqual(action_x.node_id, 'x')
        self.assertEqual(isinstance(action_x, ActionX), True)

        objecta= ObjectA()
        self.app['objecta'] = objecta
        call_actions = objecta.actions
        self.assertEqual(len(call_actions), 3)
        actions_id = [a.action.node_id for a in call_actions]
        self.assertIn('x', actions_id)
        self.assertIn('y', actions_id)
        self.assertIn('z', actions_id)
        actions_y = [a.action for a in call_actions if a.action.node_id == 'y']
        self.assertEqual(len(actions_y), 1) # LoopCardinality

        action_y = actions_y[0]
        action_y.before_execution(objecta, self.request)
        wi, proc = action_y.workitem.consume()
        wi.start_test_empty()
        self.request.bool = True
        self.request.ylc = 0
        action_y.execute(objecta, self.request, None, **{})
        self.assertIs(action_y.workitem, wi)

        workitems = proc.getWorkItems()
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 1)
        self.assertIn(u'sample.x', nodes_workitems)
        self.assertEqual(self.request.ylc, 10)

    def test_actions_YLC_TestAfter(self):
        y, pd = self._process_valid_actions()
        y._init_contexts([ActionYLC])
        self.def_container.add_definition(pd)
        self._test_actions_YLC(pd, y)

    def test_actions_YLC_TestBefore(self):
        y, pd = self._process_valid_actions()
        ActionYLC.testBefore = True
        y._init_contexts([ActionYLC])
        self.def_container.add_definition(pd)
        self._test_actions_YLC(pd, y)

    def test_actions_YLD(self):
        y, pd = self._process_valid_actions()
        y._init_contexts([ActionYLD])
        self.def_container.add_definition(pd)
        objecta= ObjectA()
        objecta.is_executed = False
        objectb= ObjectA()
        objectb.is_executed = False
        objectc= ObjectA()
        self.app['objecta'] = objecta
        self.app['objectb'] = objectb
        self.app['objectc'] = objectc
        self.request.objects = [objecta, objectb]

        start_wi = pd.start_process('x')
        actions_x = start_wi.actions
        self.assertEqual(len(actions_x), 1)
        action_x = actions_x[0]
        self.assertIs(action_x.workitem, start_wi)
        self.assertEqual(action_x.node_id, 'x')
        self.assertEqual(isinstance(action_x, ActionX), True)

        call_actions = objectc.actions
        self.assertEqual(len(call_actions), 3)
        actions_id = [a.action.node_id for a in call_actions]
        self.assertIn('x', actions_id)
        self.assertIn('y', actions_id)
        self.assertIn('z', actions_id)
        actions_y = [a.action for a in call_actions if a.action.node_id == 'y']
        self.assertEqual(len(actions_y), 1) # LoopCardinality

        action_y = actions_y[0]
        action_y.before_execution(objecta, self.request)
        wi, proc = action_y.workitem.consume()
        wi.start_test_empty()
        self.request.bool = True
        action_y.execute(objectc, self.request, None, **{})
        self.assertIs(action_y.workitem, wi)

        workitems = proc.getWorkItems()
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 1)
        self.assertIn(u'sample.x', nodes_workitems)
        self.assertEqual(objecta.is_executed, True)
        self.assertEqual(objectb.is_executed, True)

    def test_actions_steps(self):
        y, pd = self._process_valid_actions()
        y._init_contexts([ActionYSteps])
        self.def_container.add_definition(pd)
        start_wi = pd.start_process('x')
        actions_x = start_wi.actions
        self.assertEqual(len(actions_x), 1)
        action_x = actions_x[0]
        self.assertIs(action_x.workitem, start_wi)
        self.assertEqual(action_x.node_id, 'x')
        self.assertEqual(isinstance(action_x, ActionX), True)

        objecta= ObjectA()
        self.app['objecta'] = objecta
        call_actions = objecta.actions
        self.assertEqual(len(call_actions), 3)
        actions_id = [a.action.node_id for a in call_actions]
        self.assertIn('x', actions_id)
        self.assertIn('y', actions_id)
        self.assertIn('z', actions_id)
        actions_y = [a.action for a in call_actions if a.action.node_id == 'y']
        self.assertEqual(len(actions_y), 1)

        self.request.steps = []
        action_y = actions_y[0]
        action_y.before_execution(objecta, self.request)
        wi, proc = action_y.workitem.consume()
        wi.start_test_empty()
        self.assertEqual(len(action_y.stepinstances),3)
        steps = dict(action_y.stepinstances)
        self.assertIn('s1', steps)
        self.assertIn('s2', steps)
        self.assertIn('s3', steps)

        actions_y_validated_admin =  [a for a in actions_y if a.validate(objecta, self.request, **{})]
        self.assertEqual(len(actions_y_validated_admin), 1)

        s1 = steps['s1']
        s1.execute(objecta, self.request, None) #execute step1
        self.assertIs(action_y.workitem, wi)
        actions_y_executed =  [a for a in actions_y if a.isexecuted]
        self.assertEqual(len(actions_y_executed), 0)
        self.assertIn('step1',self.request.steps)

        actions_y_validated_admin =  [a for a in actions_y if a.validate(objecta, self.request, **{})]
        self.assertEqual(len(actions_y_validated_admin), 1)
        self.request.user = self.users['alice']# user == 'alice'
        actions_y_validated_alice =  [a for a in actions_y if a.validate(objecta, self.request, **{})]
        self.assertEqual(len(actions_y_validated_alice), 0)

        self.request.user = self.users['admin']
        s2 = steps['s2']
        s2.execute(objecta, self.request, None) #execute step2
        self.assertIs(action_y.workitem, wi)
        actions_y_executed =  [a for a in actions_y if a.isexecuted]
        self.assertEqual(len(actions_y_executed), 0)
        self.assertIn('step2',self.request.steps)

        actions_y_validated_admin =  [a for a in actions_y if a.validate(objecta, self.request, **{})]
        self.assertEqual(len(actions_y_validated_admin), 1)
        self.request.user = self.users['alice']# user == 'alice'
        actions_y_validated_alice =  [a for a in actions_y if a.validate(objecta, self.request, **{})]
        self.assertEqual(len(actions_y_validated_alice), 0)

        self.request.user = self.users['admin']
        s3 = steps['s3']
        s3.execute(objecta, self.request, None) #execute step2
        self.assertIs(action_y.workitem, wi)
        actions_y_executed =  [a for a in actions_y if a.isexecuted]
        self.assertEqual(len(actions_y_executed), 1)
        self.assertIn('step3',self.request.steps)

        actions_y_validated_admin =  [a for a in actions_y if a.validate(objecta, self.request, **{})]
        self.assertEqual(len(actions_y_validated_admin), 0)
        self.request.user = self.users['alice']# user == 'alice'
        actions_y_validated_alice =  [a for a in actions_y if a.validate(objecta, self.request, **{})]
        self.assertEqual(len(actions_y_validated_alice), 0)


    def test_actions_validator(self):
        y, pd = self._process_valid_actions()
        y._init_contexts([ActionY])
        self.def_container.add_definition(pd)
        start_wi = pd.start_process('x')

        objecta= ObjectA()
        self.app['objecta'] = objecta
        call_actions = objecta.actions
        actions_y = [a.action for a in call_actions if a.action.node_id == 'y']
        action_y = actions_y[0]
        action_y.before_execution(objecta, self.request)
        wi, proc = action_y.workitem.consume()
        wi.start_test_empty()
        action_y.execute(objecta, self.request, None, **{})
        validator_y = ActionY.get_validator()
        self.assertEqual(validator_y.validate(objecta, self.request), True)
        all_y = ActionY.get_allinstances( objecta, self.request)
        actions_all_y = [a for a in actions_y if a in all_y]
        self.assertEqual((action_y in all_y), False)
        self.assertEqual(len(actions_all_y), len(actions_y)-1) # -1 for action_y

    def test_actions_assignement(self):
        y, pd = self._process_valid_actions()
        y._init_contexts([ActionY])
        self.def_container.add_definition(pd)
        start_wi = pd.start_process('x')

        objecta= ObjectA()
        self.app['objecta'] = objecta
        call_actions = objecta.actions
        actions_y = [a.action for a in call_actions if a.action.node_id == 'y']
        action_y = actions_y[0]
        action_y.before_execution(objecta, self.request)
        wi, proc = action_y.workitem.consume()
        wi.start_test_empty()
        action_y.execute(objecta, self.request, None, **{})
        node_x = proc['x']
        action_x = proc['x'].workitems[0].actions[0]
        self.assertEqual(len(action_x.assigned_to), 0)
        self.assertEqual(len(node_x.assigned_to), 0)

        node_x.set_assignment(self.users['alice'])
        self.assertEqual(len(action_x.assigned_to), 1)
        self.assertEqual(len(node_x.assigned_to), 1)
        self.assertIn(self.users['alice'],action_x.assigned_to)
        self.assertIn(self.users['alice'],node_x.assigned_to)

        #admin
        self.assertEqual(action_x.validate(objecta, self.request), True)

        #bob
        self.request.user = self.users['bob']
        self.assertEqual(action_x.validate(objecta, self.request), False)

        #alice
        self.request.user = self.users['alice']
        self.assertEqual(action_x.validate(objecta, self.request), True)

        node_x.assigne_to(self.users['bob'])
        #bob
        self.request.user = self.users['bob']
        self.assertEqual(action_x.validate(objecta, self.request), True)
        self.request.user = self.users['alice']
        self.assertEqual(action_x.validate(objecta, self.request), True)
        node_x.unassigne(self.users['bob'])
        self.request.user = self.users['alice']
        self.assertEqual(action_x.validate(objecta, self.request), True)
        self.request.user = self.users['bob']
        self.assertEqual(action_x.validate(objecta, self.request), False)
        self.request.user = self.users['admin']
        self.assertEqual(action_x.validate(objecta, self.request), True)
        node_x.unassigne(self.users['alice'])
        self.request.user = self.users['bob']
        self.assertEqual(action_x.validate(objecta, self.request), True)

        action_x.set_assignment(self.users['bob'])
        self.request.user = self.users['alice']
        self.assertEqual(action_x.validate(objecta, self.request), False)
        self.request.user = self.users['bob']
        self.assertEqual(action_x.validate(objecta, self.request), True)
        self.request.user = self.users['admin']
        self.assertEqual(action_x.validate(objecta, self.request), True)
        action_x.unassigne(self.users['bob'])
        self.request.user = self.users['alice']
        self.assertEqual(action_x.validate(objecta, self.request), True)
        self.request.user = self.users['bob']
        self.assertEqual(action_x.validate(objecta, self.request), True)
        self.request.user = self.users['admin']
        self.assertEqual(action_x.validate(objecta, self.request), True)


class TestsSubProcess(FunctionalTests):

    def tearDown(self):
        registry = get_current_registry()
        registry.unregisterUtility(provided=IProcessDefinition)
        super(TestsSubProcess, self).tearDown()

    def _process_valid_subprocess(self):
        """
        S: start event
        E: end event
        G1,3(x): XOR Gateway
        P2,4(+): Parallel Gateway
        Y, Z: activities
        SP: sub-process                -----
                                    -->| SP|------------\
                                   /   -----             \
    -----   ---------   --------- /                       \   ---------   -----
    | S |-->| G1(x) |-->| P2(+) |-                         -->| P4(+) |-->| E |
    -----   --------- \ --------- \    ---------   -----   /  ---------   -----
                       \           \-->| G3(x) |-->| Y |--/
                        \              /--------   -----
                         \    -----   /
                          \-->| Z |--/
                              -----
        SS: start event
        SE: end event
        G(X): XOR Gateway
        SA, SB, SC: activities
                                     -----   -----
                                  -->| SB|-->| SE|
        -----   -----   -------- /   -----   -/---
  SP:   | SS|-->| SA|-->| G(X) |-    -----   /
        -----   -----   -------- \-->| SC|--/
                                     -----
        """
        sp = ProcessDefinition(**{'id':u'sub_process'})
        sp.isSubProcess = True
        self.app['sub_process'] = sp
        sp.defineNodes(
                ss = StartEventDefinition(),
                sa = ActivityDefinition(),
                sg = ExclusiveGatewayDefinition(),
                sb = ActivityDefinition(),
                sc = ActivityDefinition(),
                se = EndEventDefinition(),
        )
        sp.defineTransitions(
                TransitionDefinition('ss', 'sa'),
                TransitionDefinition('sa', 'sg'),
                TransitionDefinition('sg', 'sb'),
                TransitionDefinition('sg', 'sc'),
                TransitionDefinition('sb', 'se'),
                TransitionDefinition('sc', 'se'),
        )
        pd = ProcessDefinition(**{'id':u'sample'})
        self.app['sample'] = pd
        spaction = SubProcessDefinition(pd=sp)
        pd.defineNodes(
                s = StartEventDefinition(),
                sp = spaction,
                y = ActivityDefinition(),
                z = ActivityDefinition(),
                g1 = ExclusiveGatewayDefinition(),
                g2 = ParallelGatewayDefinition(),
                g3 = ExclusiveGatewayDefinition(),
                g4 = ParallelGatewayDefinition(),
                e = EndEventDefinition(),
        )
        pd.defineTransitions(
                TransitionDefinition('s', 'g1'),
                TransitionDefinition('g1', 'g2'),
                TransitionDefinition('g1', 'z'),
                TransitionDefinition('g2', 'sp'),
                TransitionDefinition('g2', 'g3'),
                TransitionDefinition('z', 'g3'),
                TransitionDefinition('g3', 'y'),
                TransitionDefinition('y', 'g4'),
                TransitionDefinition('sp', 'g4'),
                TransitionDefinition('g4', 'e'),
        )

        self.config.scan(example)
        return spaction, sp, pd


    def test_subprocess_elementary(self):
        spaction, sp, pd = self._process_valid_subprocess()
        spaction._init_contexts([ActionSP])
        self.def_container.add_definition(pd)
        self.def_container.add_definition(sp)
        start_wi = pd.start_process('sp')
        actions_sp = start_wi.actions
        self.assertEqual(len(actions_sp), 1)
        action_sp = actions_sp[0]
        self.assertIs(action_sp.workitem, start_wi)
        self.assertEqual(action_sp.node_id, 'sp')
        self.assertEqual(isinstance(action_sp, ActionSP), True)

        objecta= ObjectA()
        self.app['objecta'] = objecta
        action_sp.before_execution(objecta, self.request)
        action_sp.execute(objecta, self.request, None, **{})
        wi_sa = getWorkItem('sub_process', 'sa', self.request, objecta)
        proc =  action_sp.process
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 3)
        self.assertIn(wi_sa, workitems.values())
        workitems_keys = workitems.keys()
        wi_sp = workitems['sample.sp']
        self.assertIn('sample.sp', workitems_keys)# action is not valide
        self.assertEqual(wi_sp.actions[0].validate(objecta, self.request), False)
        self.assertIn('sample.y', workitems_keys)
        self.assertIn('sub_process.sa', workitems_keys)

        wi_sa.consume().start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 4)
        workitems_keys = workitems.keys()
        self.assertIn('sample.sp', workitems_keys)# action is not valide
        self.assertEqual(wi_sp.actions[0].validate(objecta, self.request), False)
        self.assertIn('sample.y', workitems_keys)
        self.assertIn('sub_process.sb', workitems_keys)
        self.assertIn('sub_process.sc', workitems_keys)

        wi_sb = workitems['sub_process.sb'].consume()
        wi_sb.start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 1)
        workitems_keys = workitems.keys()
        self.assertIn('sample.y', workitems_keys)

        wi_y = workitems['sample.y'].consume()
        wi_y.start_test_activity()
        wi_y.node.finish_behavior(wi_y)
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 0)

    def test_subprocess_multiinstance(self):
        spaction, sp, pd = self._process_valid_subprocess()
        spaction._init_contexts([ActionSPMI])
        self.def_container.add_definition(pd)
        self.def_container.add_definition(sp)
        objecta= ObjectA()
        objecta.is_executed = False
        objectb= ObjectA()
        objectb.is_executed = False
        objectc= ObjectA()
        self.app['objecta'] = objecta
        self.app['objectb'] = objectb
        self.app['objectc'] = objectc

        self.request.objects = [objecta, objectb]

        start_wi = pd.start_process('sp')
        actions_sp = start_wi.actions
        self.assertEqual(len(actions_sp), 3)# multi instance action and 2 actioninstance (objecta, objectb)
        actions = dict([(a.item.__name__, a) for a in actions_sp if hasattr(a, 'item') and a.item in self.request.objects])
        self.assertEqual(len(actions), 2)
        action_sp = actions['objecta']
        action_sp2 = actions['objectb']

        #sub_process 1 ('objecta')
        action_sp.before_execution(objectc, self.request)
        action_sp.execute(objectc, self.request, None, **{})
        wi_sa = getWorkItem('sub_process', 'sa', self.request, objectc)
        proc =  action_sp.process

        item = action_sp.sub_process.execution_context.involved_entity('item')
        self.assertIs(item, objecta)
        items = proc.execution_context.find_involved_entity('item')
        self.assertEqual(len(items), 1)
        self.assertIn(objecta, items)

        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 3)
        self.assertIn(wi_sa, workitems.values())
        workitems_keys = workitems.keys()
        wi_sp = workitems['sample.sp']
        self.assertIn('sample.sp', workitems_keys)# action is not valide
        self.assertEqual(wi_sp.actions[0].validate(objectc, self.request), False)
        self.assertIn('sample.y', workitems_keys)
        self.assertIn('sub_process.sa', workitems_keys)

        wi_sa.consume().start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 4)
        workitems_keys = workitems.keys()
        self.assertIn('sample.sp', workitems_keys)# action is not valide
        self.assertEqual(wi_sp.actions[0].validate(objectc, self.request), False)
        self.assertIn('sample.y', workitems_keys)
        self.assertIn('sub_process.sb', workitems_keys)
        self.assertIn('sub_process.sc', workitems_keys)

        wi_sb = workitems['sub_process.sb'].consume()
        wi_sb.start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 2)
        workitems_keys = workitems.keys()
        self.assertIn('sample.y', workitems_keys)
        self.assertIn('sample.sp', workitems_keys)

        wi_y = workitems['sample.y'].consume()
        wi_y.start_test_activity()
        wi_y.node.finish_behavior(wi_y)
        workitems = proc.getWorkItems()
        workitems_keys = workitems.keys()
        self.assertEqual(len(workitems), 1)
        self.assertIn('sample.sp', workitems_keys)

        #sub_process 2 ('objectb')
        action_sp2.before_execution(objectc, self.request)
        action_sp2.execute(objectc, self.request, None, **{})
        wi_sa = getWorkItem('sub_process', 'sa', self.request, objectc)
        proc =  action_sp2.process


        item = action_sp2.sub_process.execution_context.involved_entity('item')
        self.assertIs(item, objectb)
        items = proc.execution_context.find_involved_entity('item')
        self.assertEqual(len(items), 2)
        self.assertIn(objectb, items)
        self.assertIn(objecta, items)

        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 2)
        self.assertIn(wi_sa, workitems.values())
        workitems_keys = workitems.keys()
        wi_sp = workitems['sample.sp']
        self.assertIn('sample.sp', workitems_keys)# action is not valide
        self.assertEqual(wi_sp.actions[0].validate(objectc, self.request), False)
        self.assertIn('sub_process.sa', workitems_keys)

        wi_sa.consume().start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 3)
        workitems_keys = workitems.keys()
        self.assertIn('sample.sp', workitems_keys)# action is not valide
        self.assertEqual(wi_sp.actions[0].validate(objectc, self.request), False)
        self.assertIn('sub_process.sb', workitems_keys)
        self.assertIn('sub_process.sc', workitems_keys)

        wi_sb = workitems['sub_process.sb'].consume()
        wi_sb.start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 0)
