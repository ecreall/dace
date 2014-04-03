from dace.processinstance.gateway import ExclusiveGateway, ParallelGateway, InclusiveGateway
from .core import FlowNodeDefinition


class GatewayDefinition(FlowNodeDefinition):
    factory = NotImplemented


class ExclusiveGatewayDefinition(GatewayDefinition):
    factory = ExclusiveGateway

    def find_startable_paths(self, source_path, source):
        for transition in self.outgoing:
            if transition.condition(None):
                nodedef = self.process[transition.target.__name__]
                initial_path = source_path.clone()
                source_path.transaction.add_paths(initial_path)
                transition_path = [t for t in self.incoming if t.source is source][0]
                initial_path.add_transition(transition_path)
                startable_paths = nodedef.find_startable_paths(initial_path, self)
                for startable_path in startable_paths:
                    yield startable_path


class ParallelGatewayDefinition(GatewayDefinition):
    factory = ParallelGateway

    def find_startable_paths(self, source_path, source):
        global_transaction = source_path.transaction.get_global_transaction()
        incoming_nodes = [t.source for t in self.incoming]
        paths = []
        for n in incoming_nodes:
            paths.extend(global_transaction.find_allsubpaths_for(n))

        validated_nodes = set([p.target for p in paths])
        if (len(validated_nodes) == len(incoming_nodes)):
            for transition in self.outgoing:
                if transition.condition(None):
                    nodedef = self.process[transition.target.__name__]
                    for initial_path in paths:
                        initial_path = source_path.clone()
                        source_path.transaction.add_paths(initial_path)
                        transition_path = [t for t in self.incoming if t.source is source][0]
                        initial_path.add_transition(transition_path)
                        startable_paths = nodedef.find_startable_paths(initial_path, self)
                        for startable_path in startable_paths:
                            yield startable_path


class InclusiveGatewayDefinition(GatewayDefinition):
    factory = InclusiveGateway
