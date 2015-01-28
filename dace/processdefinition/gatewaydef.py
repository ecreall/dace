# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi

from dace.processinstance.gateway import (
    ExclusiveGateway, ParallelGateway, InclusiveGateway)
from .core import FlowNodeDefinition, Path



class GatewayDefinition(FlowNodeDefinition):
    factory = NotImplemented


class ExclusiveGatewayDefinition(GatewayDefinition):
    factory = ExclusiveGateway

    def find_startable_paths(self, source_path, source):
        for transition in self.outgoing:
            if transition.condition(None):
                nodedef = self.process[transition.target.__name__]
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
    factory = ParallelGateway

    def find_startable_paths(self, source_path, source):
        global_transaction = source_path.transaction.get_global_transaction()
        incoming_nodes = [t.source for t in self.incoming]
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

        validated_nodes = set([t.source for t in alllatest_transitions])
        validated = True
        for node in incoming_nodes:
            if not (node in  validated_nodes):
                validated = False
                break

        if validated:
            for transition in self.outgoing:
                if transition.condition(None):
                    nodedef = self.process[transition.target.__name__]
                    for path in list(paths):
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
    factory = InclusiveGateway
