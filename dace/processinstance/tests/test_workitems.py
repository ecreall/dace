# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi

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
from dace.testing import FunctionalTests


def g_b_condition(process):
    return getattr(process, 'validation_b', True)

def g_c_condition(process):
    return getattr(process, 'validation_c', True)

class TestsWorkItems(FunctionalTests):

    def tearDown(self):
        registry = get_current_registry()
        registry.unregisterUtility(provided=IProcessDefinition)
        super(TestsWorkItems, self).tearDown()

    def _process_valid_normalize(self):
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
        pd = ProcessDefinition(**{'id':u'sample'})
        self.app['sample'] = pd
        pd.defineNodes(
                s = StartEventDefinition(),
                a = ActivityDefinition(),
                b = ActivityDefinition(),
                d = ActivityDefinition(),
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

    def _process_non_valid_normalize(self):
        """
        G3(x): XOR Gateway
        G2(+): Parallel Gateway
        A, B, D: activities
                                       -----
                                    -->| A |
                                   /   -----
                        --------- /
                        | G2(+) |-
                        --------- \    ---------   -----
                                   \-->| G3(x) |-->| B |
                                       /--------   -----
                              -----   /
                              | D |--/
                              -----
        """
        pd = ProcessDefinition(**{'id':u'sample'})
        self.app['sample'] = pd
        pd.defineNodes(
                a = ActivityDefinition(),
                b = ActivityDefinition(),
                d = ActivityDefinition(),
                g2 = ParallelGatewayDefinition(),
                g3 = ExclusiveGatewayDefinition(),
        )
        pd.defineTransitions(
                TransitionDefinition('g2', 'a'),
                TransitionDefinition('g2', 'g3'),
                TransitionDefinition('d', 'g3'),
                TransitionDefinition('g3', 'b'),
        )
        pd._normalize_definition()
        self.config.scan(example)
        return pd



    def _process_valid_normalize_multiendstart(self):
        """
        G3(x): XOR Gateway
        G2(+): Parallel Gateway
        A, B, D: activities
                                       -----
                                    -->| A |
                                   /   -----
                        --------- /
                        | G2(+) |-
                        --------- \    ---------   -----
                                   \-->| G3(x) |-->| B |
                                       /--------   -----
                              -----   /
                              | D |--/
                              -----
        """
        pd = ProcessDefinition(**{'id':u'sample'})
        self.app['sample'] = pd
        pd.defineNodes(
                a = ActivityDefinition(),
                e = EndEventDefinition(),
                d = ActivityDefinition(),
                s = StartEventDefinition(),
                g3 = ExclusiveGatewayDefinition(),
        )
        pd.defineTransitions(
                TransitionDefinition('s', 'a'),
                TransitionDefinition('s', 'g3'),
                TransitionDefinition('s', 'd'),
                TransitionDefinition('d', 'g3'),
                TransitionDefinition('g3', 'e'),
                TransitionDefinition('a', 'e'),

        )
        pd._normalize_definition()
        self.config.scan(example)
        return pd

    def test_normalized_process_multistartend(self):
        pd = self._process_valid_normalize_multiendstart()
        self.def_container.add_definition(pd)
        self.assertEqual(len(pd._get_start_events()), 1)
        self.assertEqual(pd._get_start_events()[0].id, pd.id+".s")

        self.assertEqual(len(pd._get_end_events()), 1)
        self.assertEqual(pd._get_end_events()[0].id, pd.id+".e")

        start_event = pd._get_start_events()[0]
        self.assertEqual(len(start_event.outgoing), 1)
        self.assertEqual(start_event.outgoing[0].target.id, pd.id+".mergepg")
        pg = start_event.outgoing[0].target
        pg_transitions = [t.target_id for t in pg.outgoing]
        self.assertEqual(len(pg.outgoing), 3)
        self.assertIn('d', pg_transitions)
        self.assertIn('g3', pg_transitions)
        self.assertIn('a', pg_transitions)

        end_event = pd._get_end_events()[0]
        self.assertEqual(len(end_event.incoming), 1)
        self.assertEqual(end_event.incoming[0].source.id, pd.id+".mergeeg")
        eg = end_event.incoming[0].source
        eg_transitions = [t.source_id for t in eg.incoming]
        self.assertEqual(len(eg.incoming), 2)
        self.assertIn('a', eg_transitions)
        self.assertIn('g3', eg_transitions)

    def test_normalized_process(self):
        """
        S: start event (emptystart)
        E: end event (emptyend)
        G4,3(x): XOR Gateway ((G4 = endeg))
        G2,1(+): Parallel Gateway (G1 = startpg)
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
        pd = self._process_non_valid_normalize()
        self.def_container.add_definition(pd)
        self.assertEqual(len(pd._get_start_events()), 1)
        self.assertEqual(pd._get_start_events()[0].id, pd.id+".emptystart")

        self.assertEqual(len(pd._get_end_events()), 1)
        self.assertEqual(pd._get_end_events()[0].id, pd.id+".emptyend")

        start_event = pd._get_start_events()[0]
        self.assertEqual(len(start_event.outgoing), 1)
        self.assertEqual(start_event.outgoing[0].target.id, pd.id+".startpg")
        pg = start_event.outgoing[0].target
        pg_transitions = [t.target_id for t in pg.outgoing]
        self.assertEqual(len(pg.outgoing), 2)
        self.assertIn('d', pg_transitions)
        self.assertIn('g2', pg_transitions)

        end_event = pd._get_end_events()[0]
        self.assertEqual(len(end_event.incoming), 1)
        self.assertEqual(end_event.incoming[0].source.id, pd.id+".endeg")
        eg = end_event.incoming[0].source
        eg_transitions = [t.source_id for t in eg.incoming]
        self.assertEqual(len(eg.incoming), 2)
        self.assertIn('a', eg_transitions)
        self.assertIn('b', eg_transitions)

    def test_normalized_valid_process(self):
        pd = self._process_valid_normalize()
        self.def_container.add_definition(pd)

        self.assertEqual(len(pd._get_start_events()), 1)
        self.assertEqual(pd._get_start_events()[0].id, pd.id+".s")

        self.assertEqual(len(pd._get_end_events()), 1)
        self.assertEqual(pd._get_end_events()[0].id, pd.id+".e")

    def test_start_process(self):
        pd = self._process_valid_normalize()
        self.def_container.add_definition(pd)
        start_wis = pd.start_process()
        self.assertEqual(len(start_wis), 3)
        self.assertIn('a', start_wis)
        self.assertIn('b', start_wis)
        self.assertIn('d', start_wis)

    def _process_start_process(self):
        """
        S: start event
        E: end event
        G1(x): XOR Gateway
        G2,3,4(+): Parallel Gateway
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
        pd = ProcessDefinition(**{'id':u'sample'})
        self.app['sample'] = pd
        pd.defineNodes(
                s = StartEventDefinition(),
                a = ActivityDefinition(),
                b = ActivityDefinition(),
                d = ActivityDefinition(),
                g1 = ExclusiveGatewayDefinition(),
                g2 = ParallelGatewayDefinition(),
                g3 = ParallelGatewayDefinition(),
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

    def test_start_process_parallel(self):
        pd = self._process_start_process()
        self.def_container.add_definition(pd)
        start_wis = pd.start_process()
        self.assertEqual(len(start_wis), 2)
        self.assertIn('a', start_wis)
        self.assertIn('d', start_wis)

    def _process_a_g_bc(self):
        """
        S: start event
        E: end event
        G(X): XOR Gateway
        A, B, C: activities
                                     -----   -----
                                  -->| B |-->| E |
        -----   -----   -------- /   -----   -----
        | S |-->| A |-->| G(X) |-    -----
        -----   -----   -------- \-->| C |
                                     -----
        """
        pd = ProcessDefinition(**{'id':u'sample'})
        self.app['sample'] = pd
        pd.defineNodes(
                s = StartEventDefinition(),
                a = ActivityDefinition(),
                g = ExclusiveGatewayDefinition(),
                b = ActivityDefinition(),
                c = ActivityDefinition(),
                e = EndEventDefinition(),
        )
        pd.defineTransitions(
                TransitionDefinition('s', 'a'),
                TransitionDefinition('a', 'g'),
                TransitionDefinition('g', 'b'),
                TransitionDefinition('g', 'c'),
                TransitionDefinition('b', 'e'),
        )
        self.config.scan(example)
        return pd

    def test_getWorkItem_startworkitem(self):
        pd = self._process_a_g_bc()
        self.def_container.add_definition(pd)
        wi = queryWorkItem(None, self.request, 'sample', 'a')
        self.assertIsNot(wi, None)
        self.assertTrue(IStartWorkItem.providedBy(wi))
        wi = queryWorkItem(None, self.request, 'sample', 'b')
        self.assertIs(wi, None)
        wi = queryWorkItem(None, self.request, 'sample', 'c')
        self.assertIs(wi, None)


    def test_start_workitem(self):
        pd = self._process_a_g_bc()
        self.def_container.add_definition(pd)
        start_wi = pd.start_process('a')['a']
        start_swi = ISearchableObject(start_wi)
        self.assertEqual(start_swi.process_id(), 'sample')
        self.assertEqual(start_swi.node_id(), 'sample.a')
        wi, proc = start_wi.consume()
        self.assertIs(wi.node, proc['a'])

        wi.node.finish_behavior(wi)
        workitems = proc.getWorkItems()
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 2)
        self.assertIn(u'sample.b', nodes_workitems)
        self.assertIn(u'sample.c', nodes_workitems)

        dwi_b = workitems['sample.b']
        wi_b = dwi_b.consume()
        workitems = proc.getWorkItems()
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 1)
        self.assertIn(u'sample.b', nodes_workitems)

    def test_process_volatile(self):
        from dace.util import find_service
        pd = self._process_a_g_bc()
        pd.isVolatile = True
        self.def_container.add_definition(pd)
        start_wi = pd.start_process('a')['a']
        start_swi = ISearchableObject(start_wi)
        wi, proc = start_wi.consume()
        runtime = find_service('runtime')
        self.assertIs(proc.__parent__, runtime)
        wi.start_test_activity()
        workitems = proc.getWorkItems()

        dwi_b = workitems['sample.b']
        wi_b = dwi_b.consume()
        wi_b.start_test_activity()
        self.assertIs(proc.__parent__, None)

    def _process_start_complex_Exclusive_process(self):
        """
        S: start event
        E: end event
        G, 0, 1, 2(x): XOR Gateway
        P(+): Parallel Gateway
        A, B, C, D: activities
                                      -----
                                   -->| A |------------\
                                  /   -----             \
    -----   ---------  --------- /                       \        ---------   -----
    | S |-->| G(x) |-->| G0(x) |-                         ------->| G2(+) |-->| E |
    -----   ---------\ ---------\     --------    -----        /  ---------   -----
                      \         / \-->| P(+) |--->| B |-------/
                       \       /      --------\   -----      /
                   ---------  /                \    -----   /
                   | G1(x) |-/                  \-->| C |--/
                   ---------                        ----- /
                         \    -----                      /
                          \-->| D |---------------------/
                              -----
        """
        pd = ProcessDefinition(**{'id':u'sample'})
        self.app['sample'] = pd
        pd.defineNodes(
                s = StartEventDefinition(),
                a = ActivityDefinition(),
                b = ActivityDefinition(),
                c = ActivityDefinition(),
                d = ActivityDefinition(),
                g = ExclusiveGatewayDefinition(),
                g0 = ExclusiveGatewayDefinition(),
                g1 = ExclusiveGatewayDefinition(),
                p = ParallelGatewayDefinition(),
                g2 = ExclusiveGatewayDefinition(),
                e = EndEventDefinition(),
        )
        pd.defineTransitions(
                TransitionDefinition('s', 'g'),
                TransitionDefinition('g', 'g0'),
                TransitionDefinition('g', 'g1'),
                TransitionDefinition('g0', 'p'),
                TransitionDefinition('g1', 'p'),
                TransitionDefinition('g0', 'a'),
                TransitionDefinition('a', 'g2'),
                TransitionDefinition('g1', 'd'),
                TransitionDefinition('p', 'b'),
                TransitionDefinition('p', 'c'),
                TransitionDefinition('c', 'g2'),
                TransitionDefinition('b', 'g2'),
                TransitionDefinition('d', 'g2'),
                TransitionDefinition('g2', 'e'),
        )

        self.config.scan(example)
        return pd

    def test_start_complex_Exclusive_workitem_a(self):
        pd = self._process_start_complex_Exclusive_process()
        self.def_container.add_definition(pd)
        start_wis = pd.start_process()
        self.assertEqual(len(start_wis), 2)
        self.assertIn('a', start_wis)
        self.assertIn('d', start_wis)
        start_a = start_wis['a']
        wi, proc = start_a.consume()
        self.assertEqual(u'sample.a', wi.node.id)

        workitems = proc.getWorkItems()
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 1)
        self.assertIn(u'sample.a', nodes_workitems)


    def test_start_complex_Exclusive_workitem_d(self):
        pd = self._process_start_complex_Exclusive_process()
        self.def_container.add_definition(pd)
        start_wis = pd.start_process()
        self.assertEqual(len(start_wis), 2)
        self.assertIn('a', start_wis)
        self.assertIn('d', start_wis)
        start_d = start_wis['d']
        wi, proc = start_d.consume()
        self.assertEqual(u'sample.d', wi.node.id)

        workitems = proc.getWorkItems()
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 1)
        self.assertIn(u'sample.d', nodes_workitems)



    def  _process_start_complex_Parallel_process(self):
        """
        S: start event
        E: end event
        G0, 1, 2(x): XOR Gateway
        P,0(+): Parallel Gateway
        A, B, C, D: activities
                                      -----
                                   -->| A |------------\
                                  /   -----             \
    -----   ---------  --------- /                       \        ---------   -----
    | S |-->| P0(+) |-->| G0(x) |-                         ------->| G2(+) |-->| E |
    -----   ---------\ ---------\     --------    -----        /  ---------   -----
                      \         / \-->| P(+) |--->| B |-------/
                       \       /      --------\   -----      /
                   ---------  /                \    -----   /
                   | G1(x) |-/                  \-->| C |--/
                   ---------                        ----- /
                         \    -----                      /
                          \-->| D |---------------------/
                              -----
        """
        pd = ProcessDefinition(**{'id':u'sample'})
        self.app['sample'] = pd
        pd.defineNodes(
                s = StartEventDefinition(),
                a = ActivityDefinition(),
                b = ActivityDefinition(),
                c = ActivityDefinition(),
                d = ActivityDefinition(),
                p0 = ParallelGatewayDefinition(),
                g0 = ExclusiveGatewayDefinition(),
                g1 = ExclusiveGatewayDefinition(),
                p = ParallelGatewayDefinition(),
                g2 = ExclusiveGatewayDefinition(),
                e = EndEventDefinition(),
        )
        pd.defineTransitions(
                TransitionDefinition('s', 'p0'),
                TransitionDefinition('p0', 'g0'),
                TransitionDefinition('p0', 'g1'),
                TransitionDefinition('g0', 'p'),
                TransitionDefinition('g1', 'p'),
                TransitionDefinition('g0', 'a'),
                TransitionDefinition('a', 'g2'),
                TransitionDefinition('g1', 'd'),
                TransitionDefinition('p', 'b'),
                TransitionDefinition('p', 'c'),
                TransitionDefinition('c', 'g2'),
                TransitionDefinition('b', 'g2'),
                TransitionDefinition('d', 'g2'),
                TransitionDefinition('g2', 'e'),
        )

        self.config.scan(example)
        return pd

    def test_start_complex_Parallel_workitem_a(self):
        pd = self._process_start_complex_Parallel_process()
        self.def_container.add_definition(pd)
        start_wis = pd.start_process()
        self.assertEqual(len(start_wis), 4)
        self.assertIn('a', start_wis)
        self.assertIn('b', start_wis)
        self.assertIn('c', start_wis)
        self.assertIn('d', start_wis)

        start_a = start_wis['a']
        wi, proc = start_a.consume()
        self.assertEqual(u'sample.a', wi.node.id)

        workitems = proc.getWorkItems()
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 2)
        self.assertIn(u'sample.a', nodes_workitems)
        self.assertIn(u'sample.d', nodes_workitems)


    def test_start_complex_Parallel_workitem_d(self):
        pd = self._process_start_complex_Parallel_process()
        self.def_container.add_definition(pd)
        start_wis = pd.start_process()
        self.assertEqual(len(start_wis), 4)
        self.assertIn('a', start_wis)
        self.assertIn('b', start_wis)
        self.assertIn('c', start_wis)
        self.assertIn('d', start_wis)

        start_d = start_wis['d']
        wi, proc = start_d.consume()
        self.assertEqual(u'sample.d', wi.node.id)

        workitems = proc.getWorkItems()
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 2)
        self.assertIn(u'sample.a', nodes_workitems)
        self.assertIn(u'sample.d', nodes_workitems)

    def test_start_complex_Parallel_workitem_b(self):
        pd = self._process_start_complex_Parallel_process()
        self.def_container.add_definition(pd)
        start_wis = pd.start_process()
        self.assertEqual(len(start_wis), 4)
        self.assertIn('a', start_wis)
        self.assertIn('b', start_wis)
        self.assertIn('c', start_wis)
        self.assertIn('d', start_wis)

        start_b = start_wis['b']
        wi, proc = start_b.consume()
        self.assertEqual(u'sample.b', wi.node.id)

        workitems = proc.getWorkItems()
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 2)
        self.assertIn(u'sample.b', nodes_workitems)
        self.assertIn(u'sample.c', nodes_workitems)


    def  _process_start_complex_MultiDecision_process(self):
        """
        S: start event
        E: end event
        G0, 1, 2(x): XOR Gateway
        P,0(+): Parallel Gateway
        A, B, C, D, Ea: activities
                                      -----
                                   -->| A |------------\
                                  /   -----             \
    -----   ---------  --------- /                       \         ---------   -----
    | S |-->| P0(+) |-->| G0(x) |                         \------->| G2(+) |-->| E |
    -----   ---------\ ---------\     --------    -----        /   ---------   -----
               |      \          /--->| P(+) |--->| B |-------/
               |       \        /     --------\   -----      /
            -----   ---------  /               \    -----   /
            | Ea|---| G1(x) |-/                 \-->| C |--/
            -----   ---------                       ----- /
                         \    -----                      /
                          \-->| D |---------------------/
                              -----
        """
        pd = ProcessDefinition(**{'id':u'sample'})
        self.app['sample'] = pd
        pd.defineNodes(
                s = StartEventDefinition(),
                a = ActivityDefinition(),
                b = ActivityDefinition(),
                c = ActivityDefinition(),
                d = ActivityDefinition(),
                ea = ActivityDefinition(),
                p0 = ParallelGatewayDefinition(),
                g0 = ExclusiveGatewayDefinition(),
                g1 = ExclusiveGatewayDefinition(),
                p = ParallelGatewayDefinition(),
                g2 = ExclusiveGatewayDefinition(),
                e = EndEventDefinition(),
        )
        pd.defineTransitions(
                TransitionDefinition('s', 'p0'),
                TransitionDefinition('p0', 'g0'),
                TransitionDefinition('p0', 'g1'),
                TransitionDefinition('g0', 'p'),
                TransitionDefinition('g1', 'p'),
                TransitionDefinition('g0', 'a'),
                TransitionDefinition('a', 'g2'),
                TransitionDefinition('g1', 'd'),
                TransitionDefinition('p', 'b'),
                TransitionDefinition('p', 'c'),
                TransitionDefinition('c', 'g2'),
                TransitionDefinition('b', 'g2'),
                TransitionDefinition('d', 'g2'),
                TransitionDefinition('p0', 'ea'),
                TransitionDefinition('ea', 'g1'),
                TransitionDefinition('g2', 'e'),
        )

        self.config.scan(example)
        return pd


    def test_start_complex_MultiDecision_workitem_ea(self):
        pd = self._process_start_complex_MultiDecision_process()
        self.def_container.add_definition(pd)
        start_wis = pd.start_process()
        self.assertEqual(len(start_wis), 5)
        self.assertIn('a', start_wis)
        self.assertIn('b', start_wis)
        self.assertIn('c', start_wis)
        self.assertIn('d', start_wis)
        self.assertIn('ea', start_wis)

        start_ea = start_wis['ea']
        wi, proc = start_ea.consume()
        self.assertEqual(u'sample.ea', wi.node.id)
        wi.start_test_activity()
        workitems = proc.getWorkItems()
        all_workitems = proc.result_multiple
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 4)
        self.assertIn(u'sample.a', nodes_workitems)
        self.assertIn(u'sample.b', nodes_workitems)
        self.assertIn(u'sample.c', nodes_workitems)
        self.assertIn(u'sample.d', nodes_workitems)

        self.assertEqual(len(all_workitems['sample.d']), 2)#* 2
        self.assertEqual(len(all_workitems['sample.b']), 1)#* 1 (G0) une seule execution: un seul find transaction (le premier find est consomme par P0)
        self.assertEqual(len(all_workitems['sample.c']), 1)#* 1 (G0) une seule execution: un seul find transaction (le premier find est consomme par P0)

        workitems['sample.b'].consume().start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 0)

    def test_start_complex_MultiDecision_workitem_b(self):
        pd = self._process_start_complex_MultiDecision_process()
        self.def_container.add_definition(pd)
        start_wis = pd.start_process()
        self.assertEqual(len(start_wis), 5)
        self.assertIn('a', start_wis)
        self.assertIn('b', start_wis)
        self.assertIn('c', start_wis)
        self.assertIn('d', start_wis)
        self.assertIn('ea', start_wis)

        start_b = start_wis['b']
        wi, proc = start_b.consume()
        self.assertEqual(u'sample.b', wi.node.id)

        workitems = proc.getWorkItems()
        all_workitems = proc.result_multiple
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 3)
        self.assertIn(u'sample.b', nodes_workitems)
        self.assertIn(u'sample.c', nodes_workitems)
        self.assertIn(u'sample.ea', nodes_workitems)

        self.assertEqual(len(all_workitems['sample.ea']), 1)
        self.assertEqual(len(all_workitems['sample.b']), 1)
        self.assertEqual(len(all_workitems['sample.c']), 1)

        workitems['sample.ea'].start_test_activity()
        workitems = proc.getWorkItems()
        all_workitems = proc.result_multiple
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 3)
        self.assertIn(u'sample.b', nodes_workitems)
        self.assertIn(u'sample.c', nodes_workitems)
        self.assertIn(u'sample.d', nodes_workitems)

        self.assertEqual(len(all_workitems['sample.d']), 1)
        self.assertEqual(len(all_workitems['sample.b']), 1)
        self.assertEqual(len(all_workitems['sample.c']), 1)

        workitems['sample.d'].consume().start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 0)

    def test_blocked_gateway_because_no_workitems(self):
        pd = self._process_a_g_bc()
        self.def_container.add_definition(pd)
        proc = pd()
        self.app['process'] = proc
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 0)

    def _test_waiting_workitem_to_finish(self):
        pd = self._process_a_g_bc()
        self.def_container.add_definition(pd)
        start_wi = pd.start_process('a')['a']
        wi, proc = start_wi.consume()
        wi.start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 2)
        b_wi = workitems['sample.b']
        c_wi = workitems['sample.c']
        self.assertEqual(b_wi.node.id, 'sample.b')
        self.assertEqual(c_wi.node.id, 'sample.c')

        b_swi = ISearchableObject(b_wi)
        c_swi = ISearchableObject(c_wi)
        self.assertEqual(b_swi.process_id(), 'sample')
        self.assertEqual(b_swi.node_id(), 'sample.b')
        self.assertEqual(c_swi.process_id(), 'sample')
        self.assertEqual(c_swi.node_id(), 'sample.c')
        return b_wi, c_wi, proc

    def test_catalogued_workitems(self):
        b_wi, c_wi, proc = self._test_waiting_workitem_to_finish()
        request = self.request
        self.assertIs(b_wi, getWorkItem(None, request, 'sample', 'b'))
        self.assertIs(c_wi, getWorkItem(None, request, 'sample', 'c'))

    def test_waiting_workitem_b_to_finish(self):
        b_wi, c_wi, proc = self._test_waiting_workitem_to_finish()
        #import pdb; pdb.set_trace()
        b_wi.consume().start_test_activity()
        #self.assertEqual(proc.workflowRelevantData.choice, "b")
        self.assertEqual(len(proc.getWorkItems()), 0)


    def test_no_start_workitem_for_pd_subprocessOnly(self):
        pd = self._process_a_g_bc()
        self.def_container.add_definition(pd)
        start_wi = queryWorkItem(None, self.request, 'sample', 'a')
        self.assertIsNot(start_wi, None)
        pd.isControlled = True
        start_wi = queryWorkItem(None, self.request, 'sample', 'a')
        self.assertIs(start_wi, None)
        with self.assertRaises(Forbidden):
            start_wi = getWorkItem(None, self.request, 'sample', 'a')

    def _process_a_pg_bc(self):
        """
        S: start event
        E: end event
        G(+): Parallel Gateway
        A, B, C: activities
                                     -----   -----
                                  -->| B |-->| E |
        -----   -----   -------- /   -----   -----
        | S |-->| A |-->| G(+) |-    -----
        -----   -----   -------- \-->| C |
                                     -----
        """
        pd = ProcessDefinition(**{'id':u'sample'})
        self.app['sample'] = pd
        pd.defineNodes(
                s = StartEventDefinition(),
                a = ActivityDefinition(),
                g = ParallelGatewayDefinition(),
                b = ActivityDefinition(),
                c = ActivityDefinition(),
                e = EndEventDefinition(),
        )
        gb_transition = TransitionDefinition('g', 'b', g_b_condition)
        gc_transition = TransitionDefinition('g', 'c', g_c_condition)
        pd.defineTransitions(
                TransitionDefinition('s', 'a'),
                TransitionDefinition('a', 'g'),
                gb_transition,
                gc_transition,
                TransitionDefinition('c', 'e'),
                TransitionDefinition('b', 'e'),
        )
        self.config.scan(example)
        return pd

    def test_end_event_delete_all_workitems(self):
        pd = self._process_a_pg_bc()
        self.def_container.add_definition(pd)
        proc = pd()
        self.app['proc'] = proc
        self.assertEqual(len(proc.getWorkItems()), 0)
        start_wi = pd.start_process('a')['a']
        wi, proc = start_wi.consume()
        wi.start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 2)
        b_wi = workitems['sample.b']
        b_wi.consume().start_test_activity()
        self.assertEqual(len(proc.getWorkItems()), 0)

    def test_condition_not_sync_transition(self):
        pd = self._process_a_pg_bc()
        self.def_container.add_definition(pd)
        proc = pd()
        self.app['proc'] = proc
        self.assertEqual(len(proc.getWorkItems()), 0)
        start_wi = pd.start_process('a')['a']
        wi, proc = start_wi.consume()
        proc.validation_c = False
        wi.start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 1)
        b_wi = workitems['sample.b']
        self.assertTrue(b_wi.validate())
        proc.validation_c = True
        proc.validation_b = False 
        #Transition is not sync. b_wi must be valid
        self.assertTrue(b_wi.validate())
        b_wi.consume().start_test_activity()
        self.assertEqual(len(proc.getWorkItems()), 0)


    def test_condition_sync_transition(self):
        pd = self._process_a_pg_bc()
        pd['g-c'].sync = True
        pd['g-b'].sync = True
        self.def_container.add_definition(pd)
        proc = pd()
        self.app['proc'] = proc
        self.assertEqual(len(proc.getWorkItems()), 0)
        start_wi = pd.start_process('a')['a']
        wi, proc = start_wi.consume()
        proc.validation_c = False
        wi.start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 2)
        b_wi = workitems['sample.b']
        self.assertTrue(b_wi.validate())
        proc.validation_c = True
        proc.validation_b = False 
        #Transition is sync. b_wi must be not valid
        self.assertFalse(b_wi.validate())
        c_wi = workitems['sample.c']
        self.assertTrue(c_wi.validate())
        c_wi.consume().start_test_activity()
        self.assertEqual(len(proc.getWorkItems()), 0)

    def  _process_start_refresh_decision(self):
        """
        S: start event
        E: end event
        G0, 1, 2(x): XOR Gateway
        P,0(+): Parallel Gateway
        A, B, C, D, Ea: activities
                                      -----
                                   -->| A |------------\
                                  /   -----             \
    -----   ---------  --------- /                       \         ---------   -----
    | S |-->| P0(+) |-->| G0(x) |                         \------->| G2(+) |-->| E |
    -----   ---------  ---------\     --------    -----        /   ---------   -----
               |                 /--->| P(+) |--->| B |-------/
               |                /     --------\   -----      /
            -----              /               \    -----   /
            | Ea|-------------/                 \-->| C |--/
            -----                                   ----- /

        """
        pd = ProcessDefinition(**{'id':u'sample'})
        self.app['sample'] = pd
        pd.defineNodes(
                s = StartEventDefinition(),
                a = ActivityDefinition(),
                b = ActivityDefinition(),
                c = ActivityDefinition(),
                d = ActivityDefinition(),
                ea = ActivityDefinition(),
                p0 = ParallelGatewayDefinition(),
                g0 = ExclusiveGatewayDefinition(),
                p = ParallelGatewayDefinition(),
                g2 = ExclusiveGatewayDefinition(),
                e = EndEventDefinition(),
        )
        pd.defineTransitions(
                TransitionDefinition('s', 'p0'),
                TransitionDefinition('p0', 'g0'),
                TransitionDefinition('g0', 'p'),
                TransitionDefinition('g0', 'a'),
                TransitionDefinition('a', 'g2'),
                TransitionDefinition('p', 'b'),
                TransitionDefinition('p', 'c'),
                TransitionDefinition('c', 'g2'),
                TransitionDefinition('b', 'g2'),
                TransitionDefinition('d', 'g2'),
                TransitionDefinition('p0', 'ea'),
                TransitionDefinition('ea', 'p'),
                TransitionDefinition('g2', 'e'),
        )

        self.config.scan(example)
        return pd


    def test_refresh_decision(self):
        pd = self._process_start_refresh_decision()
        self.def_container.add_definition(pd)
        start_wis = pd.start_process()
        self.assertEqual(len(start_wis), 2)
        self.assertIn('a', start_wis)
        self.assertIn('ea', start_wis)

        start_ea = start_wis['ea']
        wi, proc = start_ea.consume()
        self.assertEqual(u'sample.ea', wi.node.id)
        wi.start_test_activity()
        workitems = proc.getWorkItems()
        all_workitems = proc.result_multiple
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 3)
        self.assertIn(u'sample.b', nodes_workitems)
        self.assertIn(u'sample.c', nodes_workitems)
        self.assertIn(u'sample.a', nodes_workitems)

        self.assertEqual(len(all_workitems['sample.a']), 1)
        self.assertEqual(len(all_workitems['sample.b']), 1)
        self.assertEqual(len(all_workitems['sample.c']), 1)

        workitems['sample.b'].consume()
        workitems = proc.getWorkItems()
        all_workitems = proc.result_multiple
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 2)
        self.assertIn(u'sample.b', nodes_workitems)
        self.assertIn(u'sample.c', nodes_workitems)

        self.assertEqual(len(all_workitems['sample.b']), 1)
        self.assertEqual(len(all_workitems['sample.c']), 1)

        workitems['sample.b'].start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 0)

    def  _process_start_complex_Parallel_process_decision(self):
        """
        S: start event
        E: end event
        G0, 1, 2(x): XOR Gateway
        P,0(+): Parallel Gateway
        A, B, C, D: activities
                                          -----
                                       -->| A |------------\
                                      /   -----             \
-----  ------   ---------   -------- /                       \        ---------   ------   -----
| S |->| F  |-->| P0(+) |-->| G0(x) |                         ------->| G2(+) |-->| Ae |-->| E |
-----  ------   ---------\  --------\     --------    -----        /  ---------   ------    ----
                          \         /---->| P(+) |--->| B |-------/
                           \       /      --------\   -----      /
                       ---------  /                \    -----   /
                       | G1(x) |-/                  \-->| C |--/
                       ---------                        ----- /
                             \    -----                      /
                              \-->| D |---------------------/
                                  -----
        """
        pd = ProcessDefinition(**{'id':u'sample'})
        self.app['sample'] = pd
        pd.defineNodes(
                s = StartEventDefinition(),
                a = ActivityDefinition(),
                f = ActivityDefinition(),
                b = ActivityDefinition(),
                c = ActivityDefinition(),
                d = ActivityDefinition(),
                ae = ActivityDefinition(),
                p0 = ParallelGatewayDefinition(),
                g0 = ExclusiveGatewayDefinition(),
                g1 = ExclusiveGatewayDefinition(),
                p = ParallelGatewayDefinition(),
                g2 = ExclusiveGatewayDefinition(),
                e = EndEventDefinition(),
        )
        pd.defineTransitions(
                TransitionDefinition('s', 'f'),
                TransitionDefinition('f', 'p0'),
                TransitionDefinition('p0', 'g0'),
                TransitionDefinition('p0', 'g1'),
                TransitionDefinition('g0', 'p'),
                TransitionDefinition('g1', 'p'),
                TransitionDefinition('g0', 'a'),
                TransitionDefinition('a', 'g2'),
                TransitionDefinition('g1', 'd'),
                TransitionDefinition('p', 'b'),
                TransitionDefinition('p', 'c'),
                TransitionDefinition('c', 'g2'),
                TransitionDefinition('b', 'g2'),
                TransitionDefinition('d', 'g2'),
                TransitionDefinition('g2', 'ae'),
                TransitionDefinition('ae', 'e'),
        )

        self.config.scan(example)
        return pd



    def test_start_complex_Parallel_workitem_aSync(self):
        pd = self._process_start_complex_Parallel_process_decision()
        self.def_container.add_definition(pd)
        transition = pd['p0-g0']
        transition.sync = True
        pd.bool = True
        transition.condition = example.condition
        start_wis = pd.start_process()
        self.assertEqual(len(start_wis), 1)
        self.assertIn('f', start_wis)

        start_f = start_wis['f']
        wi, proc = start_f.consume()
        self.assertEqual(u'sample.f', wi.node.id)
        wi.start_test_activity()
        workitems = dict([(k,v) for k, v in proc.getWorkItems().items() if v.validate()])
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 4)
        self.assertIn(u'sample.a', nodes_workitems)
        self.assertIn(u'sample.b', nodes_workitems)
        self.assertIn(u'sample.c', nodes_workitems)
        self.assertIn(u'sample.d', nodes_workitems)
        proc.bool = False
        workitems = dict([(k,v) for k, v in proc.getWorkItems().items() if v.validate()])
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 1)
        self.assertIn(u'sample.d', nodes_workitems)

        proc.bool = True
        workitems = dict([(k,v) for k, v in proc.getWorkItems().items() if v.validate()])
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 4)
        self.assertIn(u'sample.a', nodes_workitems)
        self.assertIn(u'sample.b', nodes_workitems)
        self.assertIn(u'sample.c', nodes_workitems)
        self.assertIn(u'sample.d', nodes_workitems)


    def test_start_complex_Parallel_workitem_decision(self):
        pd = self._process_start_complex_Parallel_process_decision()
        self.def_container.add_definition(pd)
        start_wis = pd.start_process()
        self.assertEqual(len(start_wis), 1)
        self.assertIn('f', start_wis)

        start_f = start_wis['f']
        wi, proc = start_f.consume()
        self.assertEqual(u'sample.f', wi.node.id)
        wi.start_test_activity()
        workitems = proc.getWorkItems()
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 4)
        self.assertIn(u'sample.a', nodes_workitems)
        self.assertIn(u'sample.b', nodes_workitems)
        self.assertIn(u'sample.c', nodes_workitems)
        self.assertIn(u'sample.d', nodes_workitems)

        decision_b = workitems['sample.b']
        wi = decision_b.consume()
        self.assertEqual(u'sample.b', wi.node.id)

        workitems = proc.getWorkItems()
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 2)
        self.assertIn(u'sample.b', nodes_workitems)
        self.assertIn(u'sample.c', nodes_workitems)

        wi.start_test_activity()
        workitems = proc.getWorkItems()
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 2)
        self.assertIn(u'sample.ae', nodes_workitems)
        self.assertIn(u'sample.c', nodes_workitems)

        wi = workitems['sample.c']
        wi.start_test_activity()
        workitems = proc.getWorkItems()
        all_workitems = proc.result_multiple
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 1)
        self.assertIn(u'sample.ae', nodes_workitems)
        self.assertEqual(len(all_workitems['sample.ae']), 2)# deux executions pour G2: b-->G2 et c-->G2 ====> deux DecisionWorkItem pour Ae

        decision_ae = workitems['sample.ae']
        decision_ae.consume().start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 0)

    def  _process_start_complex_Parallel_process_decision_cycle(self):
        """
        S: start event
        E: end event
        G0, 1, 2(x): XOR Gateway
        P,0(+): Parallel Gateway
        A, B, C, D: activities   |----------------------------------------|
                                 |        -----                           |
                                 |     -->| A |------------\              |
                                 |    /   -----             \             |
-----  ------   ---------   -----v-- /                       \        ---------   ------   -----
| S |->| F  |-->| P0(+) |-->| G0(x) |                         ------->| G2(x) |-->| Ae |-->| E |
-----  ------   ---------\  --------\     --------    -----         / ---------   ------    ----
                          \         /---->| P(+) |--->| B |--------/
                           \       /      --------\   -----       /
                       ---------  /                \    -----    /
                       | G1(x) |-/                  \-->| C |   /
                       ---------<----------------------------  /
                             \    -----                       /
                              \-->| D |----------------------/
                                  -----
        """
        pd = ProcessDefinition(**{'id':u'sample'})
        self.app['sample'] = pd
        pd.defineNodes(
                s = StartEventDefinition(),
                a = ActivityDefinition(),
                f = ActivityDefinition(),
                b = ActivityDefinition(),
                c = ActivityDefinition(),
                d = ActivityDefinition(),
                ae = ActivityDefinition(),
                p0 = ParallelGatewayDefinition(),
                g0 = ExclusiveGatewayDefinition(),
                g1 = ExclusiveGatewayDefinition(),
                p = ParallelGatewayDefinition(),
                g2 = ExclusiveGatewayDefinition(),
                e = EndEventDefinition(),
        )
        pd.defineTransitions(
                TransitionDefinition('s', 'f'),
                TransitionDefinition('f', 'p0'),
                TransitionDefinition('p0', 'g0'),
                TransitionDefinition('p0', 'g1'),
                TransitionDefinition('g0', 'p'),
                TransitionDefinition('g1', 'p'),
                TransitionDefinition('g0', 'a'),
                TransitionDefinition('a', 'g2'),
                TransitionDefinition('g1', 'd'),
                TransitionDefinition('p', 'b'),
                TransitionDefinition('p', 'c'),
                TransitionDefinition('c', 'g1'),
                TransitionDefinition('b', 'g2'),
                TransitionDefinition('d', 'g2'),
                TransitionDefinition('g2', 'ae'),
                TransitionDefinition('g2', 'g0'),
                TransitionDefinition('ae', 'e'),
        )

        self.config.scan(example)
        return pd

    def test_start_complex_Parallel_workitem_decision_cycle(self):
        pd = self._process_start_complex_Parallel_process_decision_cycle()
        self.def_container.add_definition(pd)
        self._test_start_complex_Parallel_workitem_decision_cycle(pd)

    #def test_boocle_dace(self): # Moyenne de 58 ms par action
    #    pd = self._process_start_complex_Parallel_process_decision_cycle()
    #    self.def_container.add_definition(pd)
    #    for x in range(1000):
    #        self._test_start_complex_Parallel_workitem_decision_cycle(pd)

    def _test_start_complex_Parallel_workitem_decision_cycle(self, pd):
        start_wis = pd.start_process()
        self.assertEqual(len(start_wis), 1)
        self.assertIn('f', start_wis)

        start_f = start_wis['f']
        wi, proc = start_f.consume()
        self.assertEqual(u'sample.f', wi.node.id)
        wi.start_test_activity()
        workitems = proc.getWorkItems()
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 4)
        self.assertIn(u'sample.a', nodes_workitems)
        self.assertIn(u'sample.b', nodes_workitems)
        self.assertIn(u'sample.c', nodes_workitems)
        self.assertIn(u'sample.d', nodes_workitems)

        decision_b = workitems['sample.b']
        wi = decision_b.consume()
        wi_a = workitems['sample.a'].consume()
        wi_c = workitems['sample.c'].consume()
        self.assertIs(wi_a, None)
        self.assertEqual(u'sample.b', wi.node.id)
        workitems = proc.getWorkItems()
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 2)
        self.assertIn(u'sample.b', nodes_workitems)
        self.assertIn(u'sample.c', nodes_workitems)
        self.assertIs(wi_c, workitems['sample.c'])

        wi.start_test_activity()
        workitems = proc.getWorkItems()
        nodes_workitems = [w for w in workitems.keys()]
        all_workitems = proc.result_multiple
        self.assertEqual(len(workitems), 3)
        self.assertIn(u'sample.ae', nodes_workitems) #b DW
        self.assertIn(u'sample.c', nodes_workitems) # P->C W
        self.assertIn(u'sample.a', nodes_workitems) #b DW
        self.assertEqual(workitems['sample.ae'].__parent__.__name__, 'b')
        self.assertEqual(workitems['sample.c'].__parent__.__name__, 'c')
        self.assertEqual(workitems['sample.a'].__parent__.__name__, 'b')
        self.assertEqual(len(all_workitems['sample.ae']), 1)

        wi = workitems['sample.a'].consume()
        wi.start_test_activity()
        workitems = proc.getWorkItems()
        all_workitems = proc.result_multiple
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 3)
        self.assertIn(u'sample.ae', nodes_workitems) #A DW
        self.assertIn(u'sample.c', nodes_workitems) # P->C W
        self.assertIn(u'sample.a', nodes_workitems) # A DW
        self.assertEqual(workitems['sample.ae'].__parent__.__name__, 'a')
        self.assertEqual(workitems['sample.c'].__parent__.__name__, 'c')
        self.assertEqual(workitems['sample.a'].__parent__.__name__, 'a')
        self.assertEqual(len(all_workitems['sample.ae']), 1)

        wi = workitems['sample.c']
        wi.start_test_activity()
        workitems = proc.getWorkItems()
        all_workitems = proc.result_multiple
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 5)
        self.assertIn(u'sample.ae', nodes_workitems)#A DW
        self.assertIn(u'sample.a', nodes_workitems) #A DW
        self.assertEqual(workitems['sample.a'].__parent__.__name__, 'a')
        self.assertEqual(workitems['sample.ae'].__parent__.__name__, 'a')
        self.assertIn(u'sample.b', nodes_workitems) #C DW
        self.assertIn(u'sample.c', nodes_workitems) #C DW
        self.assertIn(u'sample.d', nodes_workitems) #C DW
        self.assertEqual(workitems['sample.b'].__parent__.__name__, 'c')
        self.assertEqual(workitems['sample.c'].__parent__.__name__, 'c')
        self.assertEqual(workitems['sample.d'].__parent__.__name__, 'c')
        self.assertEqual(len(all_workitems['sample.ae']), 1)

        wi = workitems['sample.c'].consume()
        wi.start_test_activity()
        workitems = proc.getWorkItems()
        all_workitems = proc.result_multiple
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 2)
        self.assertIn(u'sample.b', nodes_workitems) #P->B W (execution precedente)
        self.assertIn(u'sample.d', nodes_workitems) #C DW: Pas B (encore) et C. Les transactions find sur P ne sonst pas terminees.
                                                    #      C'est le resultat du find sur C
        self.assertEqual(workitems['sample.b'].__parent__.__name__, 'b')
        self.assertEqual(workitems['sample.d'].__parent__.__name__, 'c')

        wi = workitems['sample.d'].consume()
        wi.start_test_activity()
        workitems = proc.getWorkItems()
        all_workitems = proc.result_multiple
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 3)
        self.assertIn(u'sample.ae', nodes_workitems)#D DW
        self.assertIn(u'sample.b', nodes_workitems) #P->B W
        self.assertIn(u'sample.a', nodes_workitems) #D DW
        self.assertEqual(workitems['sample.ae'].__parent__.__name__, 'd')
        self.assertEqual(workitems['sample.a'].__parent__.__name__, 'd')
        self.assertEqual(workitems['sample.b'].__parent__.__name__, 'b')
        self.assertEqual(len(all_workitems['sample.ae']), 1)

        decision_ae = workitems['sample.ae']
        decision_ae.consume().start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 0)

    def test_Transitions(self):
        pd = self._process_start_refresh_decision()
        self.def_container.add_definition(pd)
        start_wis = pd.start_process()
        self.assertEqual(len(start_wis), 2)
        self.assertIn('a', start_wis)
        self.assertIn('ea', start_wis)

        #currenttransaction = pd.global_transaction
        #self.assertEqual(len(currenttransaction.sub_transactions), 1)
        #find_transaction = currenttransaction.sub_transactions[0]
        #self.assertEqual(find_transaction.type, 'Find')
        #sources = find_transaction.path.sources
        #targets = find_transaction.path.targets
        #self.assertEqual(len(sources), 1)
        #self.assertEqual(len(targets), 1)
        #self.assertEqual(sources[0].id, 'sample.s')
        #self.assertEqual(targets[0].id, 'sample.p')

        start_ea = start_wis['ea']
        wi, proc = start_ea.consume()
        self.assertEqual(u'sample.ea', wi.node.id)
        currenttransaction = proc.global_transaction
        self.assertEqual(len(currenttransaction.sub_transactions), 3)
        find_paths = currenttransaction.find_allsubpaths_for(proc['p'])
        self.assertEqual(len(find_paths), 1)
        find_transaction = find_paths[0].transaction
        self.assertEqual(find_transaction.type, 'Find')
        sources = find_transaction.path.sources
        targets = find_transaction.path.targets
        self.assertEqual(len(sources), 1)
        self.assertEqual(len(targets), 1)
        self.assertEqual(sources[0].id, 'sample.g0')
        self.assertEqual(targets[0].id, 'sample.p')
        #ea
        startea_paths = currenttransaction.find_allsubpaths_for(proc['ea'])
        self.assertEqual(len(startea_paths), 1)
        startea_transaction = startea_paths[0].transaction
        self.assertEqual(startea_transaction.type, 'Start')
        sources = startea_transaction.path.sources
        targets = startea_transaction.path.targets
        self.assertEqual(len(sources), 1)
        self.assertEqual(len(targets), 1)
        self.assertEqual(sources[0].id, 'sample.p0')
        self.assertEqual(targets[0].id, 'sample.ea')
        #g0
        startg0_paths = currenttransaction.find_allsubpaths_for(proc['g0'])
        self.assertEqual(len(startg0_paths), 1)
        startg0_transaction = startg0_paths[0].transaction
        self.assertEqual(startg0_transaction.type, 'Start')
        sources = startg0_transaction.path.sources
        targets = startg0_transaction.path.targets
        self.assertEqual(len(sources), 1)
        self.assertEqual(len(targets), 1)
        self.assertEqual(sources[0].id, 'sample.p0')
        self.assertEqual(targets[0].id, 'sample.g0')

        startp0_paths = currenttransaction.find_allsubpaths_cross(proc['p0'])
        self.assertEqual(len(startp0_paths), 2)
        self.assertIn(startg0_paths[0], startp0_paths)
        self.assertIn(startea_paths[0], startp0_paths)

        wi.start_test_activity()
        workitems = proc.getWorkItems()
        all_workitems = proc.result_multiple
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 3)
        self.assertIn(u'sample.b', nodes_workitems)
        self.assertIn(u'sample.c', nodes_workitems)
        self.assertIn(u'sample.a', nodes_workitems)
        self.assertEqual(len(all_workitems['sample.a']), 1)
        self.assertEqual(len(all_workitems['sample.b']), 1)
        self.assertEqual(len(all_workitems['sample.c']), 1)

        currenttransaction = proc.global_transaction
        self.assertEqual(len(currenttransaction.sub_transactions), 1)
        #g0
        startg0_paths = currenttransaction.find_allsubpaths_for(proc['g0'])
        self.assertEqual(len(startg0_paths), 1)
        startg0_transaction = startg0_paths[0].transaction
        self.assertEqual(startg0_transaction.type, 'Start')
        sources = startg0_transaction.path.sources
        targets = startg0_transaction.path.targets
        self.assertEqual(len(sources), 1)
        self.assertEqual(len(targets), 1)
        self.assertEqual(sources[0].id, 'sample.p0')
        self.assertEqual(targets[0].id, 'sample.g0')

        workitems['sample.b'].consume()
        workitems = proc.getWorkItems()
        all_workitems = proc.result_multiple
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 2)
        self.assertIn(u'sample.b', nodes_workitems)
        self.assertIn(u'sample.c', nodes_workitems)

        self.assertEqual(len(all_workitems['sample.b']), 1)
        self.assertEqual(len(all_workitems['sample.c']), 1)
        currenttransaction = proc.global_transaction
        self.assertEqual(len(currenttransaction.sub_transactions), 2)
        #b
        startb_paths = currenttransaction.find_allsubpaths_for(proc['b'])
        self.assertEqual(len(startb_paths), 1)
        startb_transaction = startb_paths[0].transaction
        self.assertEqual(startb_transaction.type, 'Start')
        sources = startb_transaction.path.sources
        targets = startb_transaction.path.targets
        self.assertEqual(len(sources), 1)
        self.assertEqual(len(targets), 1)
        self.assertEqual(sources[0].id, 'sample.p')
        self.assertEqual(targets[0].id, 'sample.b')
        #c
        startc_paths = currenttransaction.find_allsubpaths_for(proc['c'])
        self.assertEqual(len(startc_paths), 1)
        startc_transaction = startc_paths[0].transaction
        self.assertEqual(startc_transaction.type, 'Start')
        sources = startc_transaction.path.sources
        targets = startc_transaction.path.targets
        self.assertEqual(len(sources), 1)
        self.assertEqual(len(targets), 1)
        self.assertEqual(sources[0].id, 'sample.p')
        self.assertEqual(targets[0].id, 'sample.c')

        workitems['sample.b'].start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 0)
        currenttransaction = proc.global_transaction
        self.assertEqual(len(currenttransaction.sub_transactions), 1)
        #c
        startc_paths = currenttransaction.find_allsubpaths_for(proc['c'])
        self.assertEqual(len(startc_paths), 1)
        startc_transaction = startc_paths[0].transaction
        self.assertEqual(startc_transaction.type, 'Start')
        sources = startc_transaction.path.sources
        targets = startc_transaction.path.targets
        self.assertEqual(len(sources), 1)
        self.assertEqual(len(targets), 1)
        self.assertEqual(sources[0].id, 'sample.p')
        self.assertEqual(targets[0].id, 'sample.c')



class TestGatewayChain(FunctionalTests):

    def tearDown(self):
        registry = get_current_registry()
        registry.unregisterUtility(provided=IProcessDefinition)
        super(TestGatewayChain, self).tearDown()

    def _process(self):
        """
        S: start event
        E: end event
        G1,3, 4(x): XOR Gateway
        G2(+): Parallel Gateway
        A, B, D: activities
                                       -----
                                    -->| A |------------\
                                   /   -----             \
    -----   ---------   --------- /                       \   ---------   -----
    | S |-->| G1(x) |-->| G2(+) |-                         -->| G4(x) |-->| E |
    -----   --------- \ --------- \    ---------   -----   /  ---------   -----
                       \           \-->| G3(x) |-->| B |--/
                        \              /--------   -----
                         \    -----   /
                          \-->| D |--/
                              -----
        """
        pd = ProcessDefinition(**{'id':u'sample'})
        self.app['sample'] = pd
        pd.defineNodes(
                s = StartEventDefinition(),
                a = ActivityDefinition(),
                b = ActivityDefinition(),
                d = ActivityDefinition(),
                g1 = ExclusiveGatewayDefinition(),
                g2 = ParallelGatewayDefinition(),
                g3 = ExclusiveGatewayDefinition(),
                g4 = ExclusiveGatewayDefinition(),
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

    def test_gateway_chain_end_event_a(self):
        pd = self._process()
        self.def_container.add_definition(pd)
        start_wi = pd.start_process('a')['a']
        wi, proc = start_wi.consume()
        wi.start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 0)

    def test_gateway_chain_end_event_d_b(self):
        pd = self._process()
        self.def_container.add_definition(pd)
        start_wi = pd.start_process('d')['d']
        wi, proc = start_wi.consume()
        wi.start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(sorted(workitems.keys()), ['sample.b'])
        workitems['sample.b'].consume().start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 0)

    def test_gateway_chain_end_event_b(self):
        pd = self._process()
        self.def_container.add_definition(pd)
        start_wi = pd.start_process('b')['b']
        wi, proc = start_wi.consume()
        wi.start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 0)

    def _process_parallel_join(self):
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
        pd = ProcessDefinition(**{'id':u'sample'})
        self.app['sample'] = pd
        pd.defineNodes(
                s = StartEventDefinition(),
                a = ActivityDefinition(),
                b = ActivityDefinition(),
                d = ActivityDefinition(),
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

    def test_gateway_chain_parallel_d_b_and_blocked(self):
        pd = self._process_parallel_join()
        self.def_container.add_definition(pd)
        start_wi = pd.start_process('d')['d']
        wi, proc = start_wi.consume()
        wi.start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(sorted(workitems.keys()), ['sample.b'])

        workitems['sample.b'].consume().start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 0)
        self.assertFalse(proc._finished)

    def test_gateway_chain_parallel_a_b(self):
        pd = self._process_parallel_join()
        self.def_container.add_definition(pd)
        start_wi = pd.start_process('a')['a']
        wi, proc = start_wi.consume()
        wi.start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(sorted(workitems.keys()), ['sample.b'])
        workitems['sample.b'].consume().start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 0)
        self.assertTrue(proc._finished)

    def test_gateway_chain_parallel_b_a(self):
        pd = self._process_parallel_join()
        self.def_container.add_definition(pd)
        start_wi = pd.start_process('b')['b']
        wi, proc = start_wi.consume()
        wi.start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(sorted(workitems.keys()), ['sample.a'])
        workitems['sample.a'].start_test_activity()
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 0)
        self.assertTrue(proc._finished)


    def  _process_start_Parallel_process_isUnique(self):
        """
        """
        pd = ProcessDefinition(**{'id':u'sample'})
        pd.isUnique = True
        self.app['sample'] = pd
        pd.defineNodes(
                s = StartEventDefinition(),
                a = ActivityDefinition(),
                b = ActivityDefinition(),
                c = ActivityDefinition(),
                p = ParallelGatewayDefinition(),
                g = ExclusiveGatewayDefinition(),
                e = EndEventDefinition(),
        )
        pd.defineTransitions(
                TransitionDefinition('s', 'p'),
                TransitionDefinition('p', 'a'),
                TransitionDefinition('p', 'b'),
                TransitionDefinition('p', 'c'),
                TransitionDefinition('c', 'g'),
                TransitionDefinition('b', 'g'),
                TransitionDefinition('a', 'g'),
                TransitionDefinition('g', 'e'),
        )

        self.config.scan(example)
        return pd

    def test_isUnique(self):
        pd = self. _process_start_Parallel_process_isUnique()
        self.def_container.add_definition(pd)
        start_wis = pd.start_process()
        self.assertEqual(len(start_wis), 3)
        self.assertIn('a', start_wis)
        self.assertIn('b', start_wis)
        self.assertIn('c', start_wis)

        start_b = start_wis['b']
        wi, proc = start_b.consume()
        self.assertEqual(u'sample.b', wi.node.id)

        workitems = proc.getWorkItems()
        self.assertIn('sample.a', workitems.keys())
        wi_a = workitems['sample.a']

        start_a = start_wis['a']
        wi2, proc2 = start_a.consume()
        self.assertIs(wi2, wi_a)
        self.assertIs(proc2, proc)



##############################################################################################


from datetime import timedelta, datetime
def time_date(process):
    return datetime.today() + timedelta(seconds=2)

def time_duration(process):
    return timedelta(seconds=2)

def return_false(process):
    return False

def return_true(process):
    return True

class EventsTests(FunctionalTests):


    def xtest_conditional_start_event(self):
        pd = self._process_a_g_bc()
        # override start event s with a condition (this is a rule start)
        pd.defineNodes(
                s = StartEventDefinition(ConditionalEventDefinition(condition=return_false)),
        )
        pd.defineTransitions(
                TransitionDefinition('s', 'a'),
        )

        self.def_container.add_definition(pd)
        start_wi = pd.start_process('s')['s']
        self.assertIs(start_wi, None)
        pd.set_start_condition(return_true)
        start_wi = pd.start_process('s')['s']
        self.assertIsNot(start_wi, None)

    def test_conditional_intermediate_event(self):
        """
        CIE: Conditional Intermediate Event
        A, B: activities

        -----   -------   -----
        | A |-->| CIE |-->| B |
        -----   -------   -----

        The CEI produces a workitem that is started.
        If condition is True, the work item is consumed and workitem B is created.
        If condition is False, the work item is blocked (coroutine).
        It is unblocked when the condition is True.
        We need to start all coroutines at application startup.
        """
        pd = ProcessDefinition(**{'id':u'sample'})
        self.app['sample'] = pd
        ced = ConditionalEventDefinition(condition=return_false)
        from dace.processinstance import event
        self.assertEqual(len(event.callbacks), 0)
        pd.defineNodes(
                a = ActivityDefinition(),
                cie = IntermediateCatchEventDefinition(ced),
                b = ActivityDefinition(),
        )
        pd.defineTransitions(
                TransitionDefinition('a', 'cie'),
                TransitionDefinition('cie', 'b'),
        )
        pd._normalize_definition()
        self.config.scan(example)
        self.def_container.add_definition(pd)
        # commit the application
        transaction.commit()
        start_wi = pd.start_process('a')['a']
        wi, proc = start_wi.consume()
        wi.start_test_activity()
        transaction.commit()
        # we need to wait ZMQStream to start on ioloop side and read
        # the DelayedCallback from the socket so we have the dc in
        # event.callbacks
        import time
        time.sleep(2.2)
        self.assertEqual(len(event.callbacks), 1)
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 1)
        self.assertEqual(sorted(workitems.keys()), ['sample.cie'])
        workitems['sample.cie'].node.eventKind.definition.condition = return_true
        workitems['sample.cie'].node.definition._p_changed = 1
        transaction.commit()
        time.sleep(6)
        transaction.begin()
        workitems = proc.getWorkItems()
        self.assertEqual(sorted(workitems.keys()), ['sample.b'])
        self.assertEqual(len(event.callbacks), 0)

    def test_timer_intermediate_event_time_duration(self):
        ted = TimerEventDefinition(time_duration=time_duration)
        self._test_timer_intermediate_event(ted)

    def test_timer_intermediate_event_time_start(self):
        ted = TimerEventDefinition(
                time_date=time_date)
        self._test_timer_intermediate_event(ted)

    def _test_timer_intermediate_event(self, ted):
        """
        S: Start Event
        e: End Event
        TIE: Timer Intermediate Event
        A, B: activities

        -----   -----   -------   -----   -----
        | S |-->| A |-->| TIE |-->| B |-->| E |
        -----   -----   -------   -----   -----

        The TEI produces a workitem.
        If start_date is equal to now, the work item is consumed and
        workitem B is created, else the work item is blocked.
        """
        pd = ProcessDefinition(**{'id':u'sample'})
        self.app['sample'] = pd
        pd.defineNodes(
                s = StartEventDefinition(),
                a = ActivityDefinition(),
                tie = IntermediateCatchEventDefinition(ted),
                b = ActivityDefinition(),
                e = EndEventDefinition(),
        )
        pd.defineTransitions(
                TransitionDefinition('s', 'a'),
                TransitionDefinition('a', 'tie'),
                TransitionDefinition('tie', 'b'),
                TransitionDefinition('b', 'e'),
        )
        self.config.scan(example)
        self.def_container.add_definition(pd)
        # commit the application
        transaction.commit()
        start_wi = pd.start_process('a')['a']
        a_wi, proc = start_wi.consume()
        a_wi.start_test_activity()
        transaction.commit()
        workitems = proc.getWorkItems()
        self.assertEqual(sorted(workitems.keys()), ['sample.tie'])
        import time
        time.sleep(6)
        transaction.begin()
        workitems = proc.getWorkItems()
        self.assertEqual(sorted(workitems.keys()), ['sample.b'])


# TODO: test event behind a xor gateway
# TODO: test parallel join gateway behind a xor gateway
