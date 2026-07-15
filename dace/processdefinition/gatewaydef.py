# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi

"""Gateway definitions.

The ``find_startable_paths`` methods are the definition-side twins of
the runtime exploration: exclusive gateways fork the exploration on
every valid outgoing transition; parallel gateways join — they only
proceed once every incoming branch has been explored (guarding against
mixed exclusive forks). Inclusive gateways are a stub.
"""
from dace.processinstance.gateway import (
    ExclusiveGateway, ParallelGateway, InclusiveGateway)
from .core import FlowNodeDefinition, Path



class GatewayDefinition(FlowNodeDefinition):
    """Base of gateway definitions."""
    factory = NotImplemented


class ExclusiveGatewayDefinition(GatewayDefinition):
    """XOR gateway definition."""
    factory = ExclusiveGateway

    def find_startable_paths(self, source_path, source):
        """Fork the startable-path exploration on every valid outgoing transition."""
        for transition in self.outgoing:
            if transition.condition(None):
                nodedef = self.process[transition.target_id]
                initial_path = source_path.clone()
                source_transaction = source_path.transaction.__parent__
                source_transaction.remove_subtransaction(
                                  source_path.transaction)
                source_transaction.start_subtransaction(type='Find', 
                                                     path=initial_path, 
                                                     initiator=self)
                initial_path.add_transition(transition)
                startable_paths = nodedef.find_startable_paths(
                                             initial_path, self)
                for startable_path in startable_paths:
                    yield startable_path


class ParallelGatewayDefinition(GatewayDefinition):
    """AND gateway definition."""
    factory = ParallelGateway

    def find_startable_paths(self, source_path, source):
        """Join logic over the ``Find`` explorations: yield outgoing paths only
        once every incoming branch arrived; abort when a fork point is an
        exclusive gateway (alternatives cannot satisfy an AND join).
        """
        global_transaction = source_path.transaction.get_global_transaction()
        paths = global_transaction.find_allsubpaths_for(self, 'Find')
        test_path = Path()
        for path in paths:
            test_path.add_transition(path.transitions)

        multiple_target = test_path.get_multiple_target
        if multiple_target:
            for node in multiple_target:
                if isinstance(self.process[node.__name__], ExclusiveGatewayDefinition):
                    return

        alllatest_transitions = []
        for path in paths:
            alllatest_transitions.extend(path.latest)

        validated_nodes = set(t.source_id for t in alllatest_transitions)
        validated = True
        incoming_nodes = (t.source_id for t in self.incoming)
        for node in incoming_nodes:
            if not node in validated_nodes:
                validated = False
                break

        if validated:
            for transition in self.outgoing:
                if transition.condition(None):
                    nodedef = self.process[transition.target_id]
                    for path in paths:
                        initial_path = path.clone()
                        source_transaction = path.transaction.__parent__
                        source_transaction.remove_subtransaction(
                                                 path.transaction)
                        source_transaction.start_subtransaction(type='Find', 
                                                            path=initial_path, 
                                                            initiator=self)
                        initial_path.add_transition(transition)
                        startable_paths = nodedef.find_startable_paths(
                                                     initial_path, self)
                        for startable_path in startable_paths:
                            yield startable_path


class InclusiveGatewayDefinition(GatewayDefinition):
    """OR gateway — **not implemented** (stub kept for the metamodel)."""
    factory = InclusiveGateway
