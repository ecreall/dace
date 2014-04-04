import zope.component
import transaction
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
    EndEventDefinition,
    IntermediateCatchEventDefinition,
    IntermediateThrowEventDefinition,
    SignalEventDefinition,
    ConditionalEventDefinition,
    TimerEventDefinition)

from dace.testing import FunctionalTests


class OldTests(FunctionalTests):

    def tearDown(self):
        registry = get_current_registry()
        registry.unregisterUtility(provided=IProcessDefinition)
        super(TestsWorkItems, self).tearDown()

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
        def ref_signal(process):
            return "X"

        pd = ProcessDefinition(u'sample')
        pd.defineActivities(
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
        zope.component.provideUtility(pd, name=pd.id)
        start_wi = pd.createStartWorkItem('sc')
        proc = start_wi.start()
        self.assertEqual(len(proc.getWorkItems()), 2)
        self.assertEqual(sorted(proc.getWorkItems().keys()), ['a', 'sc'])

    def test_signal_event(self):
        pd = self._process_definition()
        zope.component.provideUtility(pd, name=pd.id)
        start_wi = pd.createStartWorkItem('a')
        # commit the application
        transaction.commit()
        proc = start_wi.start()
        transaction.commit()

        import time
        time.sleep(6)
        transaction.begin()
        self.assertEqual(sorted(proc.getWorkItems().keys()), ['d'])

        d_wi = proc.getWorkItems()['d']
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
        def ref_signal(process):
            return "X"

        pd = ProcessDefinition(u'sample')
        pd.defineActivities(
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
        pd = self._process_definition_with_activity_after_start_event()
        zope.component.provideUtility(pd, name=pd.id)
        start_wi = pd.createStartWorkItem('b')
        # commit the application
        transaction.commit()
        proc = start_wi.start()
        transaction.commit()
        self.assertEqual(sorted(proc.getWorkItems().keys()), ['a', 'sc'])

        # simulate application shutdown
        proc.getWorkItems()['sc'].node.eventKind.stop()
        from ..subscribers import stop_ioloop
        from ..subscribers import start_ioloop
        stop_ioloop()

        # simulate application startup
        event = DatabaseOpenedWithRoot(self.app._p_jar.db())
#        from zope.event import notify
#        notify(event)
        from ..subscribers import start_intermediate_events
        start_ioloop(event)
        start_intermediate_events(event)

        a_wi = proc.getWorkItems()['a']
        a_wi.start()
        transaction.commit()

        import time
        time.sleep(6)
        transaction.begin()
        self.assertEqual(sorted(proc.getWorkItems().keys()), ['d'])
