import transaction
from pyramid.exceptions import Forbidden
from pyramid.threadlocal import get_current_registry

from dace.interfaces import IProcessDefinition, IStartWorkItem
from dace.catalog.interfaces import ISearchableObject
from dace.util import  getWorkItem, queryWorkItem
import dace.processinstance.tests.example.process as example
from dace.processdefinition.processdef import ProcessDefinition
from dace.processdefinition.activitydef import ActivityDefinition
from dace.processdefinition.gatewaydef import (
    ExclusiveGatewayDefinition, ParallelGatewayDefinition)
from dace.processdefinition.transitiondef import TransitionDefinition
from dace.processdefinition.eventdef import (
    StartEventDefinition,
    EndEventDefinition,
    IntermediateCatchEventDefinition,
    ConditionalEventDefinition,
    TimerEventDefinition)

from dace.processinstance.tests.example.process import ActionA, ActionD, ActionB
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
        G2,4(+): Parallel Gateway
        A, B, D: activities
                                       -----
                                    -->| A |------------\
                                   /   -----             \
    -----   ---------   --------- /                       \   ---------   -----
    | S |-->| G1(x) |-->| G2(+) |-                         -->| G4(+) |-->| E |
    -----   --------- \ --------- \    ---------   -----   /  ---------   -----
                       \           \-->| G3(x) |-->| B |--/
                        \              /--------   -----
                         \    -----   /
                          \-->| D |--/
                              -----
        """
        pd = ProcessDefinition(u'sample')
        self.app['pd'] = pd
        pd.defineNodes(
                s = StartEventDefinition(),
                a = ActivityDefinition(contexts=[ActionA]),
                b = ActivityDefinition(contexts=[ActionB]),
                d = ActivityDefinition(contexts=[ActionD]),
                g1 = ExclusiveGatewayDefinition(),
                g2 = ParallelGatewayDefinition(),
                g3 = ExclusiveGatewayDefinition(),
                g4 = ParallelGatewayDefinition(),
                e = EndEventDefinition(),
        )
        pd.defineTransitions(
                TransitionDefinition('s', 'g1'),
                TransitionDefinition('g1', 'g2'),
                TransitionDefinition('g1', 'd'),
                TransitionDefinition('g2', 'a'),
                TransitionDefinition('g2', 'g3'),
                TransitionDefinition('d', 'g3'),
                TransitionDefinition('g3', 'b'),
                TransitionDefinition('b', 'g4'),
                TransitionDefinition('a', 'g4'),
                TransitionDefinition('g4', 'e'),
        )

        self.config.scan(example)
        return pd

    def test_actions(self):
        pd = self._process_valid_actions()
        self.registry.registerUtility(pd, provided=IProcessDefinition, name=pd.id)
        start_wi = pd.start_process('a')
        actions_a = start_wi.actions
        self.assertEqual(len(actions_a), 1)
        action_a = actions_a[0]
        from dace.objectofcollaboration.tests.example.objects import ObjectA
        objecta= ObjectA()
        self.app['objecta'] = objecta
        actions = objecta.actions
        self.assertEqual(len(actions), 5)
        actions_id = [a.action.node_id for a in actions]
        self.assertIn('a', actions_id)
        self.assertIn('b', actions_id)
        self.assertIn('d', actions_id)
        actions_b = [a.action.node_id for a in actions if a.action.node_id == 'b']
        self.assertEqual(len(actions_b), 3)         
