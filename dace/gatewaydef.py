from .gateway import ExclusiveGateway, ParallelGateway, InclusiveGateway
from .core import FlowNodeDefinition


class GatewayDefinition(FlowNodeDefinition):
    factory = NotImplemented

    def createStartWorkItems(self, gwdef, node_ids):
        for transition in self.outgoing:
            if transition.condition(None):
                nodedef = self.process.activities[transition.to]
                for wi in nodedef.createStartWorkItems(gwdef,
                        node_ids + (transition.to,)):
                    yield wi


class ExclusiveGatewayDefinition(GatewayDefinition):
    factory = ExclusiveGateway


class ParallelGatewayDefinition(GatewayDefinition):
    factory = ParallelGateway


class InclusiveGatewayDefinition(GatewayDefinition):
    factory = InclusiveGateway


