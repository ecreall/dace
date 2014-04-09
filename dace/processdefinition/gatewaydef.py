from dace.processinstance.gateway import ExclusiveGateway, ParallelGateway, InclusiveGateway
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
                source_transaction.remove_subtransaction(source_path.transaction)
                source_transaction.start_subtransaction(type='Find', path=initial_path, initiator=self)
                initial_path.add_transition(transition)
                startable_paths = nodedef.find_startable_paths(initial_path, self)
                for startable_path in startable_paths:
                    yield startable_path


class ParallelGatewayDefinition(GatewayDefinition):
    factory = ParallelGateway

    def find_startable_paths(self, source_path, source):
        global_transaction = source_path.transaction.get_global_transaction()
        incoming_nodes = [t.source for t in self.incoming]
        paths = global_transaction.find_allsubpaths_for(self, 'Find')
        test_path = Path()
        for p in paths:
            test_path.add_transition(p.transitions)

        multiple_target = test_path.get_multiple_target()
        if multiple_target:
            for m in multiple_target:
                if isinstance(self.process[m.__name__], ExclusiveGatewayDefinition):
                    return

        alllatest_transitions = []
        for p in paths:
            alllatest_transitions.extend(p.latest)

        validated_nodes = set([t.source for t in alllatest_transitions])
        validated = True
        for n in incoming_nodes:
            if not (n in  validated_nodes):
                validated = False
                break

        if validated:
            for transition in self.outgoing:
                if transition.condition(None):
                    nodedef = self.process[transition.target.__name__]
                    for p in list(paths):
                        initial_path = p.clone()
                        source_transaction = p.transaction.__parent__
                        source_transaction.remove_subtransaction(p.transaction)
                        source_transaction.start_subtransaction(type='Find', path=initial_path, initiator=self)
                        initial_path.add_transition(transition)
                        startable_paths = nodedef.find_startable_paths(initial_path, self)
                        for startable_path in startable_paths:
                            yield startable_path


class InclusiveGatewayDefinition(GatewayDefinition):
    factory = InclusiveGateway
