# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi
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
        pd = ProcessDefinition(**{'id':u'sample'})
        self.app['sample'] = pd
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
        self.def_container.add_definition(pd)
        start_wi = pd.start_process('sc')['sc']
        sc_wi, proc = start_wi.consume()
        sc_wi.start_test_activity()
        self.assertEqual(len(proc.getWorkItems()), 2)
        self.assertEqual(sorted(proc.getWorkItems().keys()), ['sample.a', 'sample.sc'])

    def test_signal_event(self):
        pd = self._process_definition()
        self.def_container.add_definition(pd)
        start_wi = pd.start_process('a')['a']
        # commit the application
        transaction.commit()
        a_wi, proc = start_wi.consume()
        a_wi.start_test_activity()
        transaction.commit()

        import time
        time.sleep(5)
        transaction.begin()
        self.assertEqual(sorted(proc.getWorkItems().keys()), ['sample.d'])

        d_wi = proc.getWorkItems()['sample.d']
        self.assertEqual(len(proc.getWorkItems()), 1)
        self.assertEqual(sorted(proc.getWorkItems().keys()), ['sample.d'])
        d_wi.consume().start_test_activity()
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

        pd = ProcessDefinition(**{'id':u'sample'})
        self.app['sample'] = pd
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
        from dace.processinstance import event
        from dace.subscribers import stop_ioloop
        pd = self._process_definition_with_activity_after_start_event()
        self.def_container.add_definition(pd)
        start_wi = pd.start_process('b')['b']

        # commit the application
        transaction.commit()
        b_wi, proc = start_wi.consume()
        b_wi.start_test_activity()
        transaction.commit()
        self.assertEqual(sorted(proc.getWorkItems().keys()), ['sample.a', 'sample.sc'])
        # simulate application shutdown
        import time
        # we need to wait ZMQStream to start on ioloop side and read
        # the Listener from the socket so we have the listener in
        # event.callbacks
        time.sleep(2.2)
        self.assertEqual(len(event.callbacks), 1)
        stop_ioloop()
        time.sleep(1)
        self.assertEqual(len(event.callbacks), 0)

        # simulate application startup
        e = DatabaseOpenedWithRoot(self.app._p_jar.db())
        self.registry.notify(e)
        time.sleep(1)
        self.assertEqual(len(event.callbacks), 1)

        a_wi = proc.getWorkItems()['sample.a']
        a_wi.consume().start_test_activity()
        # we need to commit so the catching event Job 
        # see the modified process.
        transaction.commit()
        # The job wait 2 sec before executing

        time.sleep(5)
        transaction.begin()
        self.assertEqual(sorted(proc.getWorkItems().keys()), ['sample.d'])
