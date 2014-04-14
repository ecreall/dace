import transaction
from pyramid.threadlocal import get_current_registry

from dace.interfaces import IProcessDefinition
import dace.processinstance.tests.example.process as example
from dace.processdefinition.processdef import ProcessDefinition
from dace.processdefinition.activitydef import ActivityDefinition
from dace.processdefinition.gatewaydef import ParallelGatewayDefinition
from dace.processdefinition.transitiondef import TransitionDefinition
from dace.processdefinition.eventdef import (
    StartEventDefinition,
    EndEventDefinition,
    IntermediateCatchEventDefinition,
    IntermediateThrowEventDefinition,
    SignalEventDefinition)

from dace.testing import FunctionalTests

def ref_signal(process):
    return "X"

class TestsSignal(FunctionalTests):

    def tearDown(self):
        registry = get_current_registry()
        registry.unregisterUtility(provided=IProcessDefinition)
        super(TestsSignal, self).tearDown()

    def _process_definition(self):
        """
        G1(+), G2(+): parallel gateways
        S: start event
        E: End event
        St: Signal throwing
        Sc: Signal catching
        A, D: activities
                              -----   ------
                           -->| A |-->| St |--
        -----   --------- /   -----   ------  \ ---------   -----
        | S |-->| G1(+) |-    ------  -----    -| G2(+) |-->| E |
        -----   --------- \-->| Sc |->| D |---/ ---------   -----
                              ------  -----
        """
        pd = ProcessDefinition(u'sample')
        self.app['pd'] = pd
        pd.defineNodes(
                s = StartEventDefinition(),
                g1 = ParallelGatewayDefinition(),
                g2 = ParallelGatewayDefinition(),
                a = ActivityDefinition(),
                d = ActivityDefinition(),
                e = EndEventDefinition(),
                st = IntermediateThrowEventDefinition(
                    SignalEventDefinition(ref_signal)),
                sc = IntermediateCatchEventDefinition(
                    SignalEventDefinition(ref_signal)),
        )
        pd.defineTransitions(
                TransitionDefinition('s', 'g1'),
                TransitionDefinition('g1', 'a'),
                TransitionDefinition('g1', 'sc'),
                TransitionDefinition('a', 'st'),
                TransitionDefinition('sc', 'd'),
                TransitionDefinition('st', 'g2'),
                TransitionDefinition('d', 'g2'),
                TransitionDefinition('g2', 'e'),
        )

        self.config.scan(example)
        return pd

    def xtest_signal_event_start_sc(self):
        pd = self._process_definition()
        self.registry.registerUtility(pd, provided=IProcessDefinition, name=pd.id)
        start_wi = pd.start_process('sc')
        sc_wi, proc = start_wi.start()
        sc_wi.start()
        self.assertEqual(len(proc.getWorkItems()), 2)
        self.assertEqual(sorted(proc.getWorkItems().keys()), ['sample.a', 'sample.sc'])

    def test_signal_event(self):
        pd = self._process_definition()
        self.registry.registerUtility(pd, provided=IProcessDefinition, name=pd.id)
        start_wi = pd.start_process('a')
        # commit the application
        transaction.commit()
        a_wi, proc = start_wi.start()
        a_wi.start()
        transaction.commit()

        import time
        time.sleep(6)
        transaction.begin()
        self.assertEqual(sorted(proc.getWorkItems().keys()), ['sample.d'])

        d_wi = proc.getWorkItems()['sample.d']
        d_wi.start()
        self.assertEqual(len(proc.getWorkItems()), 0)

    def _process_definition_with_activity_after_start_event(self):
        """
        G1(+), G2(+): parallel gateways
        S: start event
        E: End event
        St: Signal throwing
        Sc: Signal catching
        A, B, D: activities
                                      -----   ------
                                   -->| A |-->| St |--
        -----   -----   --------- /   -----   ------  \ ---------   -----
        | S |-->| B |-->| G1(+) |-    ------  -----    -| G2(+) |-->| E |
        -----   -----   --------- \-->| Sc |->| D |---/ ---------   -----
                                      ------  -----
        """

        pd = ProcessDefinition(u'sample')
        self.app['pd'] = pd
        pd.defineNodes(
                s = StartEventDefinition(),
                g1 = ParallelGatewayDefinition(),
                g2 = ParallelGatewayDefinition(),
                a = ActivityDefinition(),
                b = ActivityDefinition(),
                d = ActivityDefinition(),
                e = EndEventDefinition(),
                st = IntermediateThrowEventDefinition(
                    SignalEventDefinition(ref_signal)),
                sc = IntermediateCatchEventDefinition(
                    SignalEventDefinition(ref_signal)),
        )
        pd.defineTransitions(
                TransitionDefinition('s', 'b'),
                TransitionDefinition('b', 'g1'),
                TransitionDefinition('g1', 'a'),
                TransitionDefinition('g1', 'sc'),
                TransitionDefinition('a', 'st'),
                TransitionDefinition('sc', 'd'),
                TransitionDefinition('st', 'g2'),
                TransitionDefinition('d', 'g2'),
                TransitionDefinition('g2', 'e'),
        )

        self.config.scan(example)
        return pd

    def test_start_intermediate_events_on_startup(self):
        from zope.processlifetime import DatabaseOpenedWithRoot
        from dace.processinstance.event import callbacks as event_callbacks
        pd = self._process_definition_with_activity_after_start_event()
        self.registry.registerUtility(pd, provided=IProcessDefinition, name=pd.id)
        start_wi = pd.start_process('b')

        # commit the application
        transaction.commit()
        b_wi, proc = start_wi.start()
        b_wi.start()
        transaction.commit()
        self.assertEqual(sorted(proc.getWorkItems().keys()), ['sample.a', 'sample.sc'])
        # simulate application shutdown
        self.assertEqual(len(event_callbacks), 1)
        proc.getWorkItems()['sample.sc'].node.eventKind.stop()
        self.assertEqual(len(event_callbacks), 0)
        from dace.subscribers import stop_ioloop
        stop_ioloop()

        # simulate application startup
        event = DatabaseOpenedWithRoot(self.app._p_jar.db())
        self.registry.notify(event)
        self.assertEqual(len(event_callbacks), 1)
#        from dace.subscribers import start_intermediate_events
#        start_ioloop(event)
#        start_intermediate_events(event)

        a_wi = proc.getWorkItems()['sample.a']
        a_wi.start().start()
        # we need to commit so the catching event Job 
        # see the modified process.
        transaction.commit()
        # The job wait 2 sec before executing

        import time
        time.sleep(3)
        transaction.begin()
        self.assertEqual(sorted(proc.getWorkItems().keys()), ['sample.d'])
