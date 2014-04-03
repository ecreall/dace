import transaction
import zope.component
from zope.publisher.browser import TestRequest
from zope.security.interfaces import Forbidden
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
from dace.processinstance.core import ProcessError

from dace.testing import FunctionalTests


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
        pd = ProcessDefinition(u'sample')
        self.app['pd'] = pd
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
        pd = ProcessDefinition(u'sample')
        self.app['pd'] = pd
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
        self.registry.registerUtility(pd, provided=IProcessDefinition, name=pd.id)
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
        self.registry.registerUtility(pd, provided=IProcessDefinition, name=pd.id)

        self.assertEqual(len(pd._get_start_events()), 1)
        self.assertEqual(pd._get_start_events()[0].id, pd.id+".s")

        self.assertEqual(len(pd._get_end_events()), 1)
        self.assertEqual(pd._get_end_events()[0].id, pd.id+".e")

    def test_start_process(self):
        pd = self._process_valid_normalize()
        self.registry.registerUtility(pd, provided=IProcessDefinition, name=pd.id)
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
        pd = ProcessDefinition(u'sample')
        self.app['pd'] = pd
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
        self.registry.registerUtility(pd, provided=IProcessDefinition, name=pd.id)
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
        pd = ProcessDefinition(u'sample')
        self.app['pd'] = pd
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
        self.registry.registerUtility(pd, provided=IProcessDefinition, name=pd.id)
        wi = queryWorkItem('sample', 'a', TestRequest(), None)
        self.assertIsNot(wi, None)
        self.assertTrue(IStartWorkItem.providedBy(wi))
        wi = queryWorkItem('sample', 'b', TestRequest(), None)
        self.assertIs(wi, None)
        wi = queryWorkItem('sample', 'c', TestRequest(), None)
        self.assertIs(wi, None)


    def test_start_workitem(self):
        pd = self._process_a_g_bc()
        self.registry.registerUtility(pd, provided=IProcessDefinition, name=pd.id)
        start_wi = pd.start_process('a')
        start_swi = ISearchableObject(start_wi)
        self.assertEqual(start_swi.process_id(), 'sample')
        self.assertEqual(start_swi.node_id(), 'sample.a')
        wi, proc = start_wi.start()
        self.assertIs(wi.node, proc['a'])

        wi.node.finish_behavior(wi, proc.global_transaction)
        workitems = proc.getWorkItems()
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 2)
        self.assertIn(u'sample.b', nodes_workitems)
        self.assertIn(u'sample.c', nodes_workitems)

        dwi_b = workitems['sample.b']
        wi_b = dwi_b.start()
        workitems = proc.getWorkItems()
        nodes_workitems = [w for w in workitems.keys()]
        self.assertEqual(len(workitems), 1)
        self.assertIn(u'sample.b', nodes_workitems)

##############################################################################################




    def test_blocked_gateway_because_no_workitems(self):
        pd = self._process_a_g_bc()
        self.registry.registerUtility(pd, name=pd.id)
        proc = pd()
        self.app['proc'] = proc
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 0)
        with self.assertRaises(ProcessError) as c:
            proc.start()
        self.assertEqual(c.exception.args[0],
                "Gateway blocked because there is no workitems")

    def _test_waiting_workitem_to_finish(self):
        pd = self._process_a_g_bc_with_bc_applications()
        self.registry.registerUtility(pd, name=pd.id)
        start_wi = pd.createStartWorkItem('a')
        proc = start_wi.start()
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 2)
        b_wi = workitems['b']
        c_wi = workitems['c']
        self.assertEqual(str(b_wi.node), "Activity(u'sample.b')")
        self.assertEqual(str(c_wi.node), "Activity(u'sample.c')")

        b_swi = ISearchableObject(b_wi)
        c_swi = ISearchableObject(c_wi)
        self.assertEqual(b_swi.process_id(), 'sample')
        self.assertEqual(b_swi.node_id(), 'b')
        self.assertEqual(c_swi.process_id(), 'sample')
        self.assertEqual(c_swi.node_id(), 'c')
        return b_wi, c_wi, proc

    def test_catalogued_workitems(self):
        b_wi, c_wi, proc = self._test_waiting_workitem_to_finish()
        request = TestRequest()
        self.assertIs(b_wi, getWorkItem('sample', 'b', request, None))
        self.assertIs(c_wi, getWorkItem('sample', 'c', request, None))

    def test_waiting_workitem_b_to_finish(self):
        b_wi, c_wi, proc = self._test_waiting_workitem_to_finish()
        b_wi.start()
        self.assertEqual(proc.workflowRelevantData.choice, "b")
        self.assertEqual(len(proc.getWorkItems()), 0)

    def test_waiting_workitem_c_to_finish(self):
        b_wi, c_wi, proc = self._test_waiting_workitem_to_finish()
        class Form(object):
            pass
        form = Form()
        data = {'layouts': ["azerty", "qwerty"]}
        c_wi.start(form, data)
        self.assertEqual(proc.workflowRelevantData.choice, "c: azerty")

    def test_no_start_workitem_for_pd_subprocessOnly(self):
        pd = self._process_a_g_bc_with_bc_applications()
        self.registry.registerUtility(pd, name=pd.id)
        start_wi = queryWorkItem('sample', 'a', TestRequest(), None)
        self.assertIsNot(start_wi, None)
        pd.isControlled = True
        start_wi = queryWorkItem('sample', 'a', TestRequest(), None)
        self.assertIs(start_wi, None)
        with self.assertRaises(Forbidden):
            start_wi = getWorkItem('sample', 'a', TestRequest(), None)

    def xtest_conditional_start_event(self):
        pd = self._process_a_g_bc_with_bc_applications()
        # override start event s with a condition (this is a rule start)
        pd.defineActivities(
                s = StartEventDefinition(ConditionalEventDefinition(condition=lambda self: False)),
        )
        pd.defineTransitions(
                TransitionDefinition('s', 'a'),
        )
        pd.defineApplications(
                s = Application(),
        )
        pd.activities['s'].addApplication('s')
        self.registry.registerUtility(pd, name=pd.id)
        start_wi = pd.createStartWorkItem('s')
        self.assertIs(start_wi, None)
        pd.set_start_condition(lambda self: True)
        start_wi = pd.createStartWorkItem('s')
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
        pd = ProcessDefinition(u'sample')
        ced = ConditionalEventDefinition(condition=lambda self: False)
        from dace.processinstance import event
        self.assertEqual(len(event.callbacks), 0)
        pd.defineActivities(
                a = ActivityDefinition(),
                cie = IntermediateCatchEventDefinition(ced),
                b = ActivityDefinition(),
        )
        pd.defineTransitions(
                TransitionDefinition('a', 'cie'),
                TransitionDefinition('cie', 'b'),
        )
        self.config.scan(example)
        self.registry.registerUtility(pd, name=pd.id)
        # commit the application
        transaction.commit()
        start_wi = pd.createStartWorkItem('a')
        proc = start_wi.start()
        transaction.commit()
        self.assertEqual(len(event.callbacks), 1)
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 1)
        self.assertEqual(sorted(workitems.keys()), ['cie'])
        workitems['cie'].node.eventKind.definition.condition = lambda self: True
        import time
        time.sleep(6)
        transaction.begin()
        workitems = proc.getWorkItems()
        self.assertEqual(sorted(workitems.keys()), ['b'])
        self.assertEqual(len(event.callbacks), 0)

    def test_timer_intermediate_event_time_duration(self):
        from datetime import timedelta
        ted = TimerEventDefinition(time_duration=lambda process: timedelta(seconds=2))
        self._test_timer_intermediate_event(ted)

    def test_timer_intermediate_event_time_start(self):
        from datetime import timedelta, datetime
        ted = TimerEventDefinition(
                time_date=lambda process: datetime.today() + timedelta(seconds=2))
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
        pd = ProcessDefinition(u'sample')
        pd.defineActivities(
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
        self.registry.registerUtility(pd, name=pd.id)
        # commit the application
        transaction.commit()
        start_wi = pd.createStartWorkItem('a')
        proc = start_wi.start()
        transaction.commit()
        workitems = proc.getWorkItems()
        self.assertEqual(sorted(workitems.keys()), ['tie'])
        import time
        time.sleep(6)
        transaction.begin()
        workitems = proc.getWorkItems()
        self.assertEqual(sorted(workitems.keys()), ['b'])

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
        pd = ProcessDefinition(u'sample')
        pd.defineActivities(
                s = StartEventDefinition(),
                a = ActivityDefinition(),
                g = ParallelGatewayDefinition(),
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

    def test_end_event_delete_all_workitems(self):
        pd = self._process_a_pg_bc()
        self.registry.registerUtility(pd, name=pd.id)
        proc = pd()
        self.app['proc'] = proc
        self.assertEqual(len(proc.getWorkItems()), 0)
        start_wi = pd.createStartWorkItem('a')
        proc = start_wi.start()
        workitems = proc.getWorkItems()
        self.assertEqual(len(workitems), 2)
        b_wi = workitems['b']
        b_wi.start()
        self.assertEqual(len(proc.getWorkItems()), 0)


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
        pd = ProcessDefinition(u'sample')
        pd.defineActivities(
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
        self.registry.registerUtility(pd, name=pd.id)
        start_wi = pd.createStartWorkItem('a')
        proc = start_wi.start()
        workitems = proc.getWorkItems()
        self.assertEqual(workitems.keys(), [])

    def test_gateway_chain_end_event_d_b(self):
        pd = self._process()
        self.registry.registerUtility(pd, name=pd.id)
        start_wi = pd.createStartWorkItem('d')
        proc = start_wi.start()
        workitems = proc.getWorkItems()
        self.assertEqual(sorted(workitems.keys()), ['b'])
        workitems['b'].start()
        workitems = proc.getWorkItems()
        self.assertEqual(workitems.keys(), [])

    def test_gateway_chain_end_event_b(self):
        pd = self._process()
        self.registry.registerUtility(pd, name=pd.id)
        start_wi = pd.createStartWorkItem('b')
        proc = start_wi.start()
        workitems = proc.getWorkItems()
        self.assertEqual(workitems.keys(), [])

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
        pd = ProcessDefinition(u'sample')
        self.app['pd'] = pd
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
        self.registry.registerUtility(pd, name=pd.id)
        start_wi = pd.createStartWorkItem('d')
        proc = start_wi.start()
        workitems = proc.getWorkItems()
        self.assertEqual(sorted(workitems.keys()), ['b'])
        
        workitems['b'].start()
        workitems = proc.getWorkItems()
        self.assertEqual(workitems.keys(), [])
        self.assertFalse(proc._finished)

    def test_gateway_chain_parallel_a_b(self):
        pd = self._process_parallel_join()
        self.registry.registerUtility(pd, name=pd.id)
        start_wi = pd.createStartWorkItem('a')
        proc = start_wi.start()
        workitems = proc.getWorkItems()
        self.assertEqual(sorted(workitems.keys()), ['b'])
        workitems['b'].start()
        workitems = proc.getWorkItems()
        self.assertEqual(workitems.keys(), [])
        self.assertTrue(proc._finished)

    def test_gateway_chain_parallel_b_a(self):
        pd = self._process_parallel_join()
        self.registry.registerUtility(pd, name=pd.id)
        start_wi = pd.createStartWorkItem('b')
        proc = start_wi.start()
        workitems = proc.getWorkItems()
        self.assertEqual(sorted(workitems.keys()), ['a'])
        workitems['a'].start()
        workitems = proc.getWorkItems()
        self.assertEqual(workitems.keys(), [])
        self.assertTrue(proc._finished)


# TODO: test event behind a xor gateway
# TODO: test parallel join gateway behind a xor gateway
