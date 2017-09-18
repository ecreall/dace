# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi

from pyramid.decorator import reify
from persistent.list import PersistentList
from zope.interface import implementer, Interface

from dace.interfaces import IProcessDefinition, IProcess
from .core import InvalidProcessDefinition, Transaction
from .transitiondef import TransitionDefinition
from dace.instance.process import Process
from .eventdef import StartEventDefinition, EndEventDefinition
from .gatewaydef import ParallelGatewayDefinition, ExclusiveGatewayDefinition
from dace.descriptors import CompositeMultipleProperty
from dace.util import find_catalog
from dace.model.entity import Entity


@implementer(IProcessDefinition)
class ProcessDefinition(Entity):

    nodes = CompositeMultipleProperty('nodes', 'process', True)
    transitions = CompositeMultipleProperty('transitions', 'process', True)
    TransitionDefinitionFactory = TransitionDefinition
    is_controlled = False
    is_sub_process = False
    is_volatile = False
    is_unique = False
    discriminator = 'Application'

    def __init__(self, **kwargs):
        super(ProcessDefinition, self).__init__(**kwargs)
        self.id = kwargs.get('id', None)
        self.contexts = PersistentList()

    def __call__(self, **kwargs):
        return Process(self, self._start_transition, **kwargs)

    def __repr__(self):  # pragma: no cover
        return "ProcessDefinition(%r)" % self.id

    def _dirty(self):
        try:
            del self._start_transition
        except AttributeError:
            pass

    def init_definition(self):
        pass

    def define_nodes(self, **nodes):
        self._dirty()
        for name, node in nodes.items():
            node.id = self.id + '.' + name
            node.__name__ = name
            self.addtoproperty('nodes', node)
            if hasattr(node, 'init_process_contexts'):
                node.init_process_contexts(self)

    def define_transitions(self, *transitions):
        self._dirty()
        for transition in transitions:
            transition.__name__ = transition.id
            self.addtoproperty('transitions', transition)
            transition._init_ends()

    def _is_start_orphan(self, node):
        return not isinstance(node, StartEventDefinition) and not node.incoming

    def _is_end_orphan(self, node):
        return not isinstance(node, EndEventDefinition) and not node.outgoing

    def _normalize_definition(self):
        new_transitions = ()
        orphan_nodes = [node for node in self.nodes
                        if self._is_start_orphan(node)]
        if orphan_nodes:
            start_events = self._get_start_events()
            empty_start_event = None
            if start_events:
                for s_e in start_events:
                    if s_e.event_kind is None:
                        empty_start_event = s_e
                        break

            if empty_start_event is None:
                empty_start_event = StartEventDefinition()

            p_g = ParallelGatewayDefinition()
            if empty_start_event not in self.nodes:
                self.define_nodes(emptystart=empty_start_event, startpg=p_g)
            else:
                self.define_nodes(startpg=p_g)

            oldtransitions = list(empty_start_event.outgoing)
            for oldtransition in oldtransitions:
                oldtransition.set_source(p_g)

            new_transitions += (TransitionDefinition(
                empty_start_event.__name__, 'startpg'), )
            for o_n in orphan_nodes:
                new_transitions += (TransitionDefinition(
                    'startpg', o_n.__name__), )

        if new_transitions:
            self.define_transitions(*new_transitions)
            new_transitions = ()

        orphan_nodes = [node for node in self.nodes
                        if self._is_end_orphan(node)]
        if orphan_nodes:
            end_events = self._get_end_events()
            empty_end_event = None
            if end_events:
                for e_e in end_events:
                    if e_e.event_kind is None:
                        empty_end_event = e_e
                        break

            if empty_end_event is None:
                empty_end_event = EndEventDefinition()

            e_g = ExclusiveGatewayDefinition()
            if empty_end_event not in self.nodes:
                self.define_nodes(emptyend=empty_end_event, endeg=e_g)
            else:
                self.define_nodes(endeg=e_g)

            oldtransitions = list(empty_end_event.incoming)
            for oldtransition in oldtransitions:
                oldtransition.set_target(e_g)

            new_transitions += (TransitionDefinition(
                'endeg', empty_end_event.__name__), )
            for o_n in orphan_nodes:
                new_transitions += (TransitionDefinition(
                    o_n.__name__, 'endeg'), )

        if new_transitions:
            self.define_transitions(*new_transitions)

        self._normalize_startevents()
        self._normalize_endevents()

    def _normalize_startevents(self):
        start_events = self._get_start_events()
        for s_e in start_events:
            if len(s_e.outgoing) > 1:
                p_g = ParallelGatewayDefinition()
                self.define_nodes(mergepg=p_g)
                oldtransitions = list(s_e.outgoing)
                for oldtransition in oldtransitions:
                    oldtransition.set_source(p_g)

                self.define_transitions(TransitionDefinition(
                    s_e.__name__, 'mergepg'))

    def _normalize_endevents(self):
        end_events = self._get_end_events()
        for e_e in end_events:
            if len(e_e.incoming) > 1:
                e_g = ExclusiveGatewayDefinition()
                self.define_nodes(mergeeg=e_g)
                oldtransitions = list(e_e.incoming)
                for oldtransition in oldtransitions:
                    oldtransition.set_target(e_g)

                self.define_transitions(TransitionDefinition(
                    'mergeeg', e_e.__name__))

    def _get_start_events(self):
        result = []
        for node in self.nodes:
            if isinstance(node, StartEventDefinition):
                result.append(node)

        return result

    def _get_end_events(self):
        result = []
        for node in self.nodes:
            if isinstance(node, EndEventDefinition):
                result.append(node)

        return result

    @reify
    def _start_transition(self):
        start_events = self._get_start_events()
        if len(start_events) != 1:
            raise InvalidProcessDefinition(
                "Multiple start events",
                [id for (id, a) in start_events])

        return start_events[0].outgoing[0]

    def start_process(self, node_name=None):
        if self.is_unique and self.is_started:
            if node_name:
                return {node_name: None}

            return {}

        # une transaction globale pour chaque demande
        global_transaction = Transaction()
        start_transition = self._start_transition
        startevent = start_transition.source
        # une transaction pour un evenement (pour l'instant c'est un evenement)
        sub_transaction = global_transaction.start_subtransaction(
            type='Find', initiator=self)
        start_workitems = startevent.start_process(sub_transaction)
        if node_name is None:
            return start_workitems

        return {node_name: start_workitems.get(node_name, None)}

    @property
    def is_started(self):
        dace_catalog = find_catalog('dace')
        object_provides_index = dace_catalog['object_provides']
        processid_index = dace_catalog['process_id']
        query = object_provides_index.any(
            (IProcess.__identifier__,)) & \
            processid_index.eq(self.id)
        return query.execute().__len__() > 0

    @property
    def started_processes(self):
        dace_catalog = find_catalog('dace')
        object_provides_index = dace_catalog['object_provides']
        processid_index = dace_catalog['process_id']
        query = object_provides_index.any(
            (IProcess.__identifier__,)) & \
            processid_index.eq(self.id)
        return list(query.execute().all())
