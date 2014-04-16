import transaction
from pyramid.exceptions import Forbidden
from pyramid.threadlocal import get_current_registry

from dace.interfaces import IProcessDefinition
import dace.processinstance.tests.example.process as example
from dace.processdefinition.processdef import ProcessDefinition
from dace.processdefinition.activitydef import ActivityDefinition
from dace.processdefinition.gatewaydef import (
    ExclusiveGatewayDefinition, ParallelGatewayDefinition)
from dace.processdefinition.transitiondef import TransitionDefinition
from dace.processdefinition.eventdef import (
    StartEventDefinition,
    EndEventDefinition)

from dace.processinstance.tests.example.process import (
    ActionX, 
    ActionY, 
    ActionZ)
from dace.interfaces import IProcessDefinition
from dace.objectofcollaboration.tests.example.objects import ObjectA
from dace.testing import FunctionalTests
from ..process import Process


class TestsProcessRelations(FunctionalTests):

    def tearDown(self):
        registry = get_current_registry()
        registry.unregisterUtility(provided=IProcessDefinition)
        super(TestsProcessRelations, self).tearDown()

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
        pd = ProcessDefinition(u'sample')
        self.app['pd'] = pd
        pd.defineNodes(
                s = StartEventDefinition(),
                x = ActivityDefinition(contexts=[ActionX]),
                y = ActivityDefinition(contexts = [ActionY]),
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
        return pd

    def test_add_involved(self):
        pd = self._process_valid_actions()
        self.registry.registerUtility(pd, provided=IProcessDefinition, name=pd.id)
        objecta= ObjectA()
        objectb= ObjectA()
        objectc= ObjectA()
        self.app['objecta'] = objecta
        self.app['objectb'] = objectb
        self.app['objectc'] = objectc
        call_actions = objecta.actions
        actions_id = [a.action.node_id for a in call_actions]
        actions_y = [a.action for a in call_actions if a.action.node_id == 'y']
        action_y = actions_y[0]
        action_y.before_execution(objecta, self.request)
        wi, proc = action_y.workitem.consume()

        ec = proc.execution_context
        relationC1 = ec.get_involved_entity('realtion1')
        self.assertIs(relationC1, None)
        relationsC1 = ec.get_involved_entities('realtion1')
        self.assertEqual(len(relationsC1), 0)

        ec.add_involved_entity('realtion1', objecta)
        relation1 = ec.get_involved_entity('realtion1')
        self.assertIs(relation1, objecta)

        self.assertIs(objecta.creator, None)
        involvers = objecta.involvers
        self.assertEqual(len(involvers), 1)
        self.assertIs(involvers[0], proc)

        relations1 = ec.get_involved_entities('realtion1')
        self.assertEqual(len(relations1), 1)
        all_relations = ec.get_involved_entities()
        self.assertEqual(len(all_relations), 1)
        self.assertIs(relations1[0], all_relations[0])

        ec.remove_involved_entity('realtion1', objecta)
        relation1 = ec.get_involved_entity('realtion1')
        self.assertIs(relation1, None)
        relations1 = ec.get_involved_entities('realtion1')
        self.assertEqual(len(relations1), 0)
        all_relations = ec.get_involved_entities()
        self.assertEqual(len(all_relations), 0)

        ec.add_involved_entity('realtion1', objecta)
        ec.add_involved_entity('realtion1', objectb)
        relation1 = ec.get_involved_entity('realtion1')
        self.assertIs(relation1, objectb)
        relations1 = ec.get_involved_entities('realtion1')
        self.assertEqual(len(relations1), 2)
        all_relations = ec.get_involved_entities()
        self.assertEqual(len(all_relations), 2)
        self.assertIs(relations1[0], all_relations[0])
        self.assertIs(relations1[1], all_relations[1])

        ec.remove_involved_entity('realtion1', objectb)
        ec.add_involved_entity('realtion1', objectc)
        relation1 = ec.get_involved_entity('realtion1')
        self.assertIs(relation1, objectc)
        relations1 = ec.get_involved_entities('realtion1')
        self.assertEqual(len(relations1), 2)
        all_relations = ec.get_involved_entities()
        self.assertEqual(len(all_relations), 2)
        self.assertIs(relations1[0], all_relations[0])
        self.assertIs(relations1[1], all_relations[1])

    def test_add_created(self):
        pd = self._process_valid_actions()
        self.registry.registerUtility(pd, provided=IProcessDefinition, name=pd.id)
        objecta= ObjectA()
        objectb= ObjectA()
        objectc= ObjectA()
        self.app['objecta'] = objecta
        self.app['objectb'] = objectb
        self.app['objectc'] = objectc
        call_actions = objecta.actions
        actions_id = [a.action.node_id for a in call_actions]
        actions_y = [a.action for a in call_actions if a.action.node_id == 'y']
        action_y = actions_y[0]
        action_y.before_execution(objecta, self.request)
        wi, proc = action_y.workitem.consume()

        ec = proc.execution_context
        relationC1 = ec.get_created_entity('realtion1')
        self.assertIs(relationC1, None)
        relationsC1 = ec.get_created_entities('realtion1')
        self.assertEqual(len(relationsC1), 0)

        ec.add_created_entity('realtion1', objecta)
        relationC1 = ec.get_created_entity('realtion1')
        relationI1 = ec.get_involved_entity('realtion1')
        self.assertIs(relationC1, objecta)

        self.assertIs(objecta.creator, proc)
        involvers = objecta.involvers
        self.assertEqual(len(involvers), 1)
        self.assertIs(involvers[0], proc)

        self.assertIs(relationI1, objecta)
        relationsC1 = ec.get_created_entities('realtion1')
        relationsI1 = ec.get_involved_entities('realtion1')
        self.assertEqual(len(relationsC1), 1)
        self.assertEqual(len(relationsI1), 1)
        
        ec = proc.execution_context
        all_relationsC = ec.get_created_entities()
        all_relationsI = ec.get_involved_entities()
        self.assertEqual(len(all_relationsC), 1)
        self.assertEqual(len(all_relationsI), 1)
        self.assertIs(relationsC1[0], all_relationsC[0])

        ec.remove_created_entity('realtion1', objecta)
        relationI1 = ec.get_involved_entity('realtion1')
        self.assertIs(relationI1, None)
        relationsC1 = ec.get_created_entities('realtion1')
        self.assertEqual(len(relationC1), 0)
        all_relationsC = ec.get_created_entities()
        self.assertEqual(len(all_relationsC), 0)

        ec.add_created_entity('realtion1', objecta)
        ec.add_created_entity('realtion1', objectb)
        relation1 = ec.get_created_entity('realtion1')
        self.assertIs(relation1, objectb)
        relations1 = ec.get_created_entities('realtion1')
        self.assertEqual(len(relations1), 2)
        all_relations = ec.get_created_entities()
        self.assertEqual(len(all_relations), 2)
        self.assertIs(relations1[0], all_relations[0])
        self.assertIs(relations1[1], all_relations[1])

        ec.remove_created_entity('realtion1', objectb)
        ec.add_created_entity('realtion1', objectc)
        relation1 = ec.get_created_entity('realtion1')
        self.assertIs(relation1, objectc)
        relations1 = ec.get_created_entities('realtion1')
        self.assertEqual(len(relations1), 2)
        all_relations = ec.get_created_entities()
        self.assertEqual(len(all_relations), 2)
        self.assertIs(relations1[0], all_relations[0])
        self.assertIs(relations1[1], all_relations[1])
        self.assertEqual(ec.has_relation(objectb), False)
        self.assertEqual(ec.has_relation(objecta), True)
        self.assertEqual(ec.has_relation(objecta, 'realtion1'), True)
        self.assertEqual(ec.has_relation(objectc, 'realtion2'), False)

    def test_add_involved_collection(self):
        pd = self._process_valid_actions()
        self.registry.registerUtility(pd, provided=IProcessDefinition, name=pd.id)
        objecta= ObjectA()
        objectb= ObjectA()
        objectc= ObjectA()
        self.app['objecta'] = objecta
        self.app['objectb'] = objectb
        self.app['objectc'] = objectc
        call_actions = objecta.actions
        actions_id = [a.action.node_id for a in call_actions]
        actions_y = [a.action for a in call_actions if a.action.node_id == 'y']
        action_y = actions_y[0]
        action_y.before_execution(objecta, self.request)
        wi, proc = action_y.workitem.consume()

        ec = proc.execution_context
        relationC1 = ec.get_involved_collection('realtion1')
        self.assertIs(relationC1, None)

        ec.add_involved_collection('realtion1', [objecta, objectb])
        relation1 = ec.get_involved_collection('realtion1')
        self.assertEqual(len(relation1), 2)
        self.assertIn(objecta, relation1)
        self.assertIn(objectb, relation1)

        self.assertIs(objecta.creator, None)
        involvers = objecta.involvers
        self.assertEqual(len(involvers), 1)
        self.assertIs(involvers[0], proc)

        all_relations = ec.get_involved_entities()
        self.assertEqual(len(all_relations), 2)
        self.assertIn(objecta, all_relations)
        self.assertIn(objectb, all_relations)

        ec.remove_involved_collection('realtion1', [objecta])
        relation1 = ec.get_involved_collection('realtion1')
        self.assertEqual(len(relation1), 1)
        self.assertIn(objectb, relation1)

        ec.add_involved_collection('realtion1', [objecta, objectc])
        relation1 = ec.get_involved_collection('realtion1')
        self.assertEqual(len(relation1), 2)
        self.assertIn(objecta, relation1)
        self.assertIn(objectc, relation1)

        relation1 = ec.get_involved_collections('realtion1')
        self.assertEqual(len(relation1), 2)
        self.assertEqual(len(relation1[0]), 1)
        self.assertEqual(len(relation1[1]), 2)
        self.assertIn(objecta, relation1[1])
        self.assertIn(objectc, relation1[1])
        self.assertIn(objectb, relation1[0])

    def test_add_created_collection(self):
        pd = self._process_valid_actions()
        self.registry.registerUtility(pd, provided=IProcessDefinition, name=pd.id)
        objecta= ObjectA()
        objectb= ObjectA()
        objectc= ObjectA()
        self.app['objecta'] = objecta
        self.app['objectb'] = objectb
        self.app['objectc'] = objectc
        call_actions = objecta.actions
        actions_id = [a.action.node_id for a in call_actions]
        actions_y = [a.action for a in call_actions if a.action.node_id == 'y']
        action_y = actions_y[0]
        action_y.before_execution(objecta, self.request)
        wi, proc = action_y.workitem.consume()

        ec = proc.execution_context
        relationC1 = ec.get_created_collection('realtion1')
        self.assertIs(relationC1, None)

        ec.add_created_collection('realtion1', [objecta, objectb])
        relation1 = ec.get_created_collection('realtion1')
        self.assertEqual(len(relation1), 2)
        self.assertIn(objecta, relation1)
        self.assertIn(objectb, relation1)

        self.assertIs(objecta.creator, proc)
        involvers = objecta.involvers
        self.assertEqual(len(involvers), 1)
        self.assertIs(involvers[0], proc)

        all_relations = ec.get_involved_entities()
        self.assertEqual(len(all_relations), 2)
        self.assertIn(objecta, all_relations)
        self.assertIn(objectb, all_relations)

        ec.remove_created_collection('realtion1', [objecta])
        relation1 = ec.get_involved_collection('realtion1')
        self.assertEqual(len(relation1), 1)
        self.assertIn(objectb, relation1)

        relation1 = ec.get_created_collection('realtion1')
        self.assertEqual(len(relation1), 1)
        self.assertIn(objectb, relation1)

        ec.add_created_collection('realtion1', [objecta, objectc])
        relation1 = ec.get_created_collection('realtion1')
        self.assertEqual(len(relation1), 2)
        self.assertIn(objecta, relation1)
        self.assertIn(objectc, relation1)

        relation1 = ec.get_created_collections('realtion1')
        self.assertEqual(len(relation1), 2)
        self.assertEqual(len(relation1[0]), 1)
        self.assertEqual(len(relation1[1]), 2)
        self.assertIn(objecta, relation1[1])
        self.assertIn(objectc, relation1[1])
        self.assertIn(objectb, relation1[0])

    def test_add_data(self):
        pd = self._process_valid_actions()
        self.registry.registerUtility(pd, provided=IProcessDefinition, name=pd.id)
        objecta= ObjectA()
        objectb= ObjectA()
        objectc= ObjectA()
        self.app['objecta'] = objecta
        self.app['objectb'] = objectb
        self.app['objectc'] = objectc
        call_actions = objecta.actions
        actions_id = [a.action.node_id for a in call_actions]
        actions_y = [a.action for a in call_actions if a.action.node_id == 'y']
        action_y = actions_y[0]
        action_y.before_execution(objecta, self.request)
        wi, proc = action_y.workitem.consume()

        ec = proc.execution_context
        ec.add_data('data1', 4)
        ec.add_data('data2', objecta)

        self.assertEqual(ec.get_data('data1'), 4)
        self.assertEqual(ec.get_data('data2'), objecta)

        ec.add_data('data1', 5)
        self.assertEqual(ec.get_data('data1'), 5)
        self.assertEqual(ec.get_data('data1', 0), 4)


        
