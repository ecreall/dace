# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi
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
        pd = ProcessDefinition(**{'id':u'sample'})
        self.app['sample'] = pd
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
        self.def_container.add_definition(pd)
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
        relationC1 = ec.involved_entity('realtion1')
        self.assertIs(relationC1, None)
        relationsC1 = ec.involved_entities('realtion1')
        self.assertEqual(len(relationsC1), 0)

        ec.add_involved_entity('realtion1', objecta)
        relation1 = ec.involved_entity('realtion1')
        self.assertIs(relation1, objecta)

        self.assertIs(objecta.creator, None)
        involvers = objecta.involvers
        self.assertEqual(len(involvers), 1)
        self.assertIs(involvers[0], proc)

        relations1 = ec.involved_entities('realtion1')
        self.assertEqual(len(relations1), 1)
        all_relations = ec.involved_entities()
        self.assertEqual(len(all_relations), 1)
        self.assertIs(relations1[0], all_relations[0])

        ec.remove_entity('realtion1', objecta)
        relation1 = ec.involved_entity('realtion1')
        self.assertIs(relation1, None)
        relations1 = ec.involved_entities('realtion1')
        self.assertEqual(len(relations1), 0)
        all_relations = ec.involved_entities()
        self.assertEqual(len(all_relations), 0)

        ec.add_involved_entity('realtion1', objecta)
        ec.add_involved_entity('realtion1', objectb)
        relation1 = ec.involved_entity('realtion1')
        self.assertIs(relation1, objectb)
        relations1 = ec.involved_entities('realtion1')
        self.assertEqual(len(relations1), 2)
        all_relations = ec.involved_entities()
        self.assertEqual(len(all_relations), 2)
        self.assertIs(relations1[0], all_relations[0])
        self.assertIs(relations1[1], all_relations[1])

        ec.remove_entity('realtion1', objectb)
        ec.add_involved_entity('realtion1', objectc)
        relation1 = ec.involved_entity('realtion1')
        self.assertIs(relation1, objectc)
        relations1 = ec.involved_entities('realtion1')
        self.assertEqual(len(relations1), 2)
        all_relations = ec.involved_entities()
        self.assertEqual(len(all_relations), 2)
        self.assertIs(relations1[0], all_relations[0])
        self.assertIs(relations1[1], all_relations[1])

    def test_add_created(self):
        pd = self._process_valid_actions()
        self.def_container.add_definition(pd)
        objecta= ObjectA()
        objectb= ObjectA()
        objectc= ObjectA()
        self.app['objecta'] = objecta
        self.app['objectb'] = objectb
        self.app['objectc'] = objectc
        call_actions = objecta.actions
        actions_y = [a.action for a in call_actions if a.action.node_id == 'y']
        action_y = actions_y[0]
        action_y.before_execution(objecta, self.request)
        wi, proc = action_y.workitem.consume()

        ec = proc.execution_context
        relationC1 = ec.created_entity('realtion1')
        self.assertIs(relationC1, None)
        relationsC1 = ec.created_entities('realtion1')
        self.assertEqual(len(relationsC1), 0)

        active_ivs = ec.all_active_involveds()
        self.assertEqual(len(active_ivs.keys()), 0)

        ec.add_created_entity('realtion1', objecta)
        relationC1 = ec.created_entity('realtion1')
        relationI1 = ec.involved_entity('realtion1')
        self.assertIs(relationC1, objecta)


        active_ivs = ec.all_active_involveds()
        self.assertEqual(len(active_ivs.keys()), 1)
        self.assertEqual('element', active_ivs['realtion1']['type'])
        self.assertIn('realtion1', active_ivs)
        self.assertIn(objecta, active_ivs['realtion1']['entities'])


        self.assertIs(objecta.creator, proc)
        involvers = objecta.involvers
        self.assertEqual(len(involvers), 1)
        self.assertIs(involvers[0], proc)

        self.assertIs(relationI1, objecta)
        relationsC1 = ec.created_entities('realtion1')
        relationsI1 = ec.involved_entities('realtion1')
        self.assertEqual(len(relationsC1), 1)
        self.assertEqual(len(relationsI1), 1)
        
        ec = proc.execution_context
        all_relationsC = ec.created_entities()
        all_relationsI = ec.involved_entities()
        self.assertEqual(len(all_relationsC), 1)
        self.assertEqual(len(all_relationsI), 1)
        self.assertIs(relationsC1[0], all_relationsC[0])

        ec.remove_entity('realtion1', objecta)
        relationI1 = ec.involved_entity('realtion1')
        self.assertIs(relationI1, None)
        relationsC1 = ec.created_entities('realtion1')
        self.assertEqual(len(relationC1), 0)
        all_relationsC = ec.created_entities()
        self.assertEqual(len(all_relationsC), 0)

        ec.add_created_entity('realtion1', objecta)
        ec.add_created_entity('realtion1', objectb)
        relation1 = ec.created_entity('realtion1')
        self.assertIs(relation1, objectb)

        active_ivs = ec.all_active_involveds()
        self.assertEqual(len(active_ivs.keys()), 1)
        self.assertEqual('element', active_ivs['realtion1']['type'])
        self.assertIn('realtion1', active_ivs)
        self.assertEqual(len(active_ivs['realtion1']['entities']), 1)
        self.assertIn(objectb, active_ivs['realtion1']['entities'])


        relations1 = ec.created_entities('realtion1')
        self.assertEqual(len(relations1), 2)
        all_relations = ec.created_entities()
        self.assertEqual(len(all_relations), 2)
        self.assertIs(relations1[0], all_relations[0])
        self.assertIs(relations1[1], all_relations[1])

        ec.remove_entity('realtion1', objectb)
        ec.add_created_entity('realtion1', objectc)
        relation1 = ec.created_entity('realtion1')
        self.assertIs(relation1, objectc)


        active_ivs = ec.all_active_involveds()
        self.assertEqual(len(active_ivs.keys()), 1)
        self.assertIn('realtion1', active_ivs)
        self.assertEqual('element', active_ivs['realtion1']['type'])
        self.assertEqual(len(active_ivs['realtion1']['entities']), 1)
        self.assertIn(objectc, active_ivs['realtion1']['entities'])

        relations1 = ec.created_entities('realtion1')
        self.assertEqual(len(relations1), 2)
        all_relations = ec.created_entities()
        self.assertEqual(len(all_relations), 2)
        self.assertIs(relations1[0], all_relations[0])
        self.assertIs(relations1[1], all_relations[1])
        self.assertEqual(ec.has_relation(objectb), False)
        self.assertEqual(ec.has_relation(objecta), True)
        self.assertEqual(ec.has_relation(objecta, 'realtion1'), True)
        self.assertEqual(ec.has_relation(objectc, 'realtion2'), False)

    def test_add_involved_collection(self):
        pd = self._process_valid_actions()
        self.def_container.add_definition(pd)
        objecta= ObjectA()
        objectb= ObjectA()
        objectc= ObjectA()
        self.app['objecta'] = objecta
        self.app['objectb'] = objectb
        self.app['objectc'] = objectc
        call_actions = objecta.actions
        actions_y = [a.action for a in call_actions if a.action.node_id == 'y']
        action_y = actions_y[0]
        action_y.before_execution(objecta, self.request)
        wi, proc = action_y.workitem.consume()

        ec = proc.execution_context
        relationC1 = ec.involved_collection('realtion1')
        self.assertEqual(len(relationC1), 0)

        active_ivs = ec.all_active_involveds()
        self.assertEqual(len(active_ivs.keys()), 0)

        ec.add_involved_collection('realtion1', [objecta, objectb])
        relation1 = ec.involved_collection('realtion1')
        self.assertEqual(len(relation1), 2)
        self.assertIn(objecta, relation1)
        self.assertIn(objectb, relation1)

        active_ivs = ec.all_active_involveds()
        self.assertEqual(len(active_ivs.keys()), 1)
        self.assertIn('realtion1', active_ivs.keys())
        self.assertEqual(len(active_ivs['realtion1']['entities']), 2)
        self.assertEqual('collection', active_ivs['realtion1']['type'])
        self.assertIn(objecta, active_ivs['realtion1']['entities'])
        self.assertIn(objectb, active_ivs['realtion1']['entities'])

        self.assertIs(objecta.creator, None)
        involvers = objecta.involvers
        self.assertEqual(len(involvers), 1)
        self.assertIs(involvers[0], proc)

        all_relations = ec.involved_entities()
        self.assertEqual(len(all_relations), 2)
        self.assertIn(objecta, all_relations)
        self.assertIn(objectb, all_relations)

        ec.remove_collection('realtion1', [objecta])
        relation1 = ec.involved_collection('realtion1')
        self.assertEqual(len(relation1), 1)
        self.assertIn(objectb, relation1)

        active_ivs = ec.all_active_involveds()
        self.assertEqual(len(active_ivs.keys()), 1)
        self.assertIn('realtion1', active_ivs)
        self.assertEqual('collection', active_ivs['realtion1']['type'])
        self.assertEqual(len(active_ivs['realtion1']['entities']), 1)
        self.assertIn(objectb, active_ivs['realtion1']['entities'])

        ec.add_involved_collection('realtion1', [objecta, objectc])
        relation1 = ec.involved_collection('realtion1')
        self.assertEqual(len(relation1), 2)
        self.assertIn(objecta, relation1)
        self.assertIn(objectc, relation1)

        active_ivs = ec.all_active_involveds()
        self.assertEqual(len(active_ivs.keys()), 1)
        self.assertIn('realtion1', active_ivs)
        self.assertEqual('collection', active_ivs['realtion1']['type'])
        self.assertEqual(len(active_ivs['realtion1']['entities']), 2)
        self.assertIn(objecta, active_ivs['realtion1']['entities'])
        self.assertIn(objectc, active_ivs['realtion1']['entities'])

        relation1 = ec.involved_collections('realtion1')
        self.assertEqual(len(relation1), 2)
        self.assertEqual(len(relation1[0]), 1)
        self.assertEqual(len(relation1[1]), 2)
        self.assertIn(objecta, relation1[1])
        self.assertIn(objectc, relation1[1])
        self.assertIn(objectb, relation1[0])

    def test_add_created_collection(self):
        pd = self._process_valid_actions()
        self.def_container.add_definition(pd)
        objecta= ObjectA()
        objectb= ObjectA()
        objectc= ObjectA()
        self.app['objecta'] = objecta
        self.app['objectb'] = objectb
        self.app['objectc'] = objectc
        call_actions = objecta.actions
        actions_y = [a.action for a in call_actions if a.action.node_id == 'y']
        action_y = actions_y[0]
        action_y.before_execution(objecta, self.request)
        wi, proc = action_y.workitem.consume()

        ec = proc.execution_context
        relationC1 = ec.created_collection('realtion1')
        self.assertEqual(len(relationC1), 0)

        ec.add_created_collection('realtion1', [objecta, objectb])
        relation1 = ec.created_collection('realtion1')
        self.assertEqual(len(relation1), 2)
        self.assertIn(objecta, relation1)
        self.assertIn(objectb, relation1)

        self.assertIs(objecta.creator, proc)
        involvers = objecta.involvers
        self.assertEqual(len(involvers), 1)
        self.assertIs(involvers[0], proc)

        all_relations = ec.involved_entities()
        self.assertEqual(len(all_relations), 2)
        self.assertIn(objecta, all_relations)
        self.assertIn(objectb, all_relations)

        ec.remove_collection('realtion1', [objecta])
        relation1 = ec.involved_collection('realtion1')
        self.assertEqual(len(relation1), 1)
        self.assertIn(objectb, relation1)

        relation1 = ec.created_collection('realtion1')
        self.assertEqual(len(relation1), 1)
        self.assertIn(objectb, relation1)

        ec.add_created_collection('realtion1', [objecta, objectc])
        relation1 = ec.created_collection('realtion1')
        self.assertEqual(len(relation1), 2)
        self.assertIn(objecta, relation1)
        self.assertIn(objectc, relation1)

        relation1 = ec.created_collections('realtion1')
        self.assertEqual(len(relation1), 2)
        self.assertEqual(len(relation1[0]), 1)
        self.assertEqual(len(relation1[1]), 2)
        self.assertIn(objecta, relation1[1])
        self.assertIn(objectc, relation1[1])
        self.assertIn(objectb, relation1[0])

    def test_add_data(self):
        pd = self._process_valid_actions()
        self.def_container.add_definition(pd)
        objecta= ObjectA()
        objectb= ObjectA()
        objectc= ObjectA()
        self.app['objecta'] = objecta
        self.app['objectb'] = objectb
        self.app['objectc'] = objectc
        call_actions = objecta.actions
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

    def test_sub_executionContext(self):
        from ..process import ExecutionContext
        objecta= ObjectA()
        objectb= ObjectA()
        objectc= ObjectA()
        objectd= ObjectA()
        self.app['objecta'] = objecta
        self.app['objectb'] = objectb
        self.app['objectc'] = objectc
        self.app['objectd'] = objectd
        ec1= ExecutionContext()
        ec2= ExecutionContext()
        ec3= ExecutionContext()
        ec4= ExecutionContext()
        ec5= ExecutionContext()
        self.app['ec1'] = ec1
        self.app['ec2'] = ec2
        self.app['ec3'] = ec3
        self.app['ec4'] = ec4
        self.app['ec5'] = ec5
        ec1.add_sub_execution_context(ec2)
        ec1.add_sub_execution_context(ec3)
        ec3.add_sub_execution_context(ec4)
        ec3.add_sub_execution_context(ec5)

        self.assertEqual(len(ec1.sub_execution_contexts), 2)
        self.assertEqual(len(ec3.sub_execution_contexts), 2)
        self.assertEqual(len(ec2.sub_execution_contexts), 0)
        self.assertEqual(len(ec4.sub_execution_contexts), 0)
        self.assertEqual(len(ec5.sub_execution_contexts), 0)

        self.assertIn(ec3, ec1.sub_execution_contexts)
        self.assertIn(ec2, ec1.sub_execution_contexts)
        self.assertIn(ec4, ec3.sub_execution_contexts)
        self.assertIn(ec5, ec3.sub_execution_contexts)

        ec4.add_created_collection('relation1', [objecta, objectb])
        ec2.add_created_collection('relation2', [objectc, objectd])

        involved_entities_ec4 = ec4.involved_entities('relation1')
        involved_entities_ec2 = ec2.involved_entities('relation2')
        self.assertEqual(len(involved_entities_ec4), 2)
        self.assertEqual(len(involved_entities_ec2), 2)
        self.assertIn(objecta, involved_entities_ec4)
        self.assertIn(objectb, involved_entities_ec4)
        self.assertIn(objectc, involved_entities_ec2)
        self.assertIn(objectd, involved_entities_ec2)

        created_entities_ec4 = ec4.created_entities('relation1')
        created_entities_ec2 = ec2.created_entities('relation2')
        self.assertEqual(len(created_entities_ec4), 2)
        self.assertEqual(len(created_entities_ec2), 2)
        self.assertIn(objecta, created_entities_ec4)
        self.assertIn(objectb, created_entities_ec4)
        self.assertIn(objectc, created_entities_ec2)
        self.assertIn(objectd, created_entities_ec2)

        relation1_ec5 = ec5.created_collection('relation1')
        self.assertEqual(len(relation1_ec5), 2)
        self.assertIn(objecta, relation1_ec5)
        self.assertIn(objectb, relation1_ec5)
        
        self.assertEqual(ec5.has_relation(objecta, 'relation1'), True)
        self.assertEqual(ec5.has_relation(objectb, 'relation1'), True)
        self.assertEqual(ec5.has_relation(objectb, 'relation2'), False)
        self.assertEqual(ec5.has_relation(objecta, 'relation2'), False)
        self.assertEqual(ec5.has_relation(objectc, 'relation2'), True)
        self.assertEqual(ec5.has_relation(objectd, 'relation2'), True)
        self.assertEqual(ec5.has_relation(objectc, 'relation1'), False)
        self.assertEqual(ec5.has_relation(objectd, 'relation1'), False)

        relation2_ec5 = ec5.created_collection('relation2')
        self.assertEqual(len(relation2_ec5), 2)
        self.assertIn(objectc, relation2_ec5)
        self.assertIn(objectd, relation2_ec5)


        relation1_ec5 = ec5.involved_collection('relation1')
        self.assertEqual(len(relation1_ec5), 2)
        self.assertIn(objecta, relation1_ec5)
        self.assertIn(objectb, relation1_ec5)

        relation_ec5 = ec5.created_collections()
        self.assertEqual(len(relation_ec5), 2)
        allrelations = relation_ec5[0]
        allrelations.extend(relation_ec5[1])
        self.assertEqual(len(allrelations), 4)
        self.assertIn(objecta, allrelations)
        self.assertIn(objectb, allrelations)
        self.assertIn(objectc, allrelations)
        self.assertIn(objectd, allrelations)

        relation_ec5 = ec5.involved_collections()
        self.assertEqual(len(relation_ec5), 2)
        allrelations = relation_ec5[0]
        allrelations.extend(relation_ec5[1])
        self.assertEqual(len(allrelations), 4)
        self.assertIn(objecta, allrelations)
        self.assertIn(objectb, allrelations)
        self.assertIn(objectc, allrelations)
        self.assertIn(objectd, allrelations)

        all_involveds = ec5.all_involveds()
        self.assertEqual(len(all_involveds), 4)
        self.assertIn(objecta, all_involveds)
        self.assertIn(objectb, all_involveds)
        self.assertIn(objectc, all_involveds)
        self.assertIn(objectd, all_involveds)

        entity = ec5.created_entity('relation1')
        self.assertIn(entity, [objecta, objectb]) 

        entity = ec5.involved_entity('relation1')
        self.assertIn(entity, [objecta, objectb])

        relation1_e5 = ec5.involved_collection('relation1', 3)
        self.assertEqual(len(relation1_e5), 0)
        relation1_e5 = ec5.created_collection('relation1', 3)    
        self.assertEqual(len(relation1_e5), 0)

        ec4.remove_collection('relation1', [objecta])
        all_involveds = ec5.all_involveds()
        self.assertEqual(len(all_involveds), 3)
        self.assertIn(objectb, all_involveds)
        self.assertIn(objectc, all_involveds)
        self.assertIn(objectd, all_involveds)

        ec4.remove_collection('relation3', [objecta])
        involved_entities_ec4 = ec4.involved_entities('relation1')
        self.assertEqual(len(involved_entities_ec4), 1)
        self.assertIn(objectb, involved_entities_ec4)

        ec2.add_data('data1', 4)
        self.assertEqual(ec5.get_data('data1'), 4)
        self.assertEqual(ec3.get_data('data1'), 4)
        self.assertEqual(ec1.get_data('data1'), 4)
        self.assertEqual(ec4.get_data('data1'), 4)
        self.assertEqual(ec2.get_data('data1'), 4)
        ec2.add_data('data1', 5)
        self.assertEqual(ec5.get_data('data1'), 5)
        self.assertEqual(ec3.get_data('data1'), 5)
        self.assertEqual(ec1.get_data('data1'), 5)
        self.assertEqual(ec4.get_data('data1'), 5)
        self.assertEqual(ec2.get_data('data1'), 5)
        ec5.add_data('data1', 6)
        self.assertEqual(ec5.get_data('data1'), 6)
        self.assertEqual(ec2.get_data('data1'), 5)
        datas1_ec3 = ec3.find_data('data1')
        self.assertEqual(len(datas1_ec3), 2)
        self.assertIn(6, datas1_ec3)
        self.assertIn(5, datas1_ec3)

        ec1.remove_sub_execution_context(ec5)
        self.assertIn(ec5, ec3.sub_execution_contexts)

        ec3.remove_sub_execution_context(ec5)
        datas1_ec3 = ec3.find_data('data1')
        self.assertEqual(len(datas1_ec3), 1)
        self.assertIn(5, datas1_ec3)
