from pyramid.threadlocal import get_current_registry
from substanced.events import ObjectAddedEvent

from .core import ActivityFinished, ActivityStarted, ProcessError, FlowNode
from .event import Event


class Gateway(FlowNode):

    def _refreshWorkItems(self):
        # Unindexes workitems
        for wi in self.workitems.values():
            wi[0].remove()
        self.workitems.clear()
        workitems = {}
        i = 0
        for workitem_tuple in self._createWorkItems(self, ()):
            i += 1
            workitem_tuple[0].id = i
            workitems[i] = workitem_tuple

        self.workitems = workitems
        # Indexes workitems
        registry = get_current_registry()
        for wi in self.workitems.values():
            registry.notify(ObjectAddedEvent(wi[0]))

    def createWorkItems(self, gw, allowed_transitions):
        for transition in allowed_transitions:
            node = self.process.nodes[transition.to]
            for wi_tuple in node._createWorkItems(gw, (transition.to,)):
               yield wi_tuple


# non parallel avec condition avec default
class ExclusiveGateway(Gateway):
    incoming = ()
    def start(self, transition):
        self._define_next_replay_node()
        definition = self.definition
        registry = get_current_registry()
        notify = registry.notify
        notify(ActivityStarted(self))
        if self._v_next_replay_node is not None:
            for transition in definition.outgoing:
                if transition.to == self._v_next_replay_node:
                    notify(ActivityFinished(self))
                    self.process.transition(self, [transition])
                    return

        # Check all direct transitions
        allowed_transitions = []
        for transition in definition.outgoing:
            if transition.sync or transition.condition(self.process):
                allowed_transitions.append(transition)

        # If we only have one, execute it
        if len(allowed_transitions) == 1:
            notify(ActivityFinished(self))
            self.process.transition(self, allowed_transitions)
            return

        # We can't decide which transition to execute
        # We create all possible work items from here
        workitems = {}
        i = 0
        created_workitems = self.createWorkItems(self,
                                                 allowed_transitions)
        for workitem_tuple in created_workitems:
            i += 1
            workitem_tuple[0].id = i
            workitems[i] = workitem_tuple

        if not workitems:
            raise ProcessError("Gateway blocked because there is no workitems")

        self.workitems = workitems
        # Indexes workitems
        for wi in self.workitems.values():
            notify(ObjectAddedEvent(wi[0]))

        for transition in allowed_transitions:
            next = self.process.nodes[transition.to]
            if isinstance(next, Event):
                next.prepare()

    def workItemFinished(self, work_item, *results):
        # beginning exactly the same as Activity
        unused, app, formal, actual = self.workitems.pop(work_item.id)
        self._p_changed = True
        work_item.remove()
        res = results
        for parameter, name in zip(formal, actual):
            # save all input parameters as output
            if parameter.input:
                v = res[0]
                res = res[1:]
                setattr(self.process.workflowRelevantData, name, v)

        if res:
            raise TypeError("Too many results")
        # end

        # clear other work items
        for wi in self.workitems.values():
            wi[0].node.stop()
            wi[0].remove()
        self.workitems.clear()
        # finish this gateway
        registry = get_current_registry()
        registry.notify(ActivityFinished(self))

        self.process._v_toreplay = work_item.node_ids
        self.process._v_toreplay_app = work_item.application
        next_node_id = work_item.node_ids[0]
        transition = [t for t in self.definition.outgoing if t.to == next_node_id][0]
        self.process.transition(self, [transition])

    def _createWorkItems(self, gw, node_ids):
        process = gw.process
        for transition in self.definition.outgoing:
            if transition.sync or transition.condition(process):
                node = process.nodes[transition.to]
                for wi_tuple in node._createWorkItems(gw,
                        node_ids + (transition.to,)):
                    yield wi_tuple


# parallel sans condition sans default
class ParallelGateway(Gateway):

    incoming = ()
    def start(self, transition):
        self._define_next_replay_node()

        # Start the activity, if we've had enough incoming transitions

        definition = self.definition

        if transition in self.incoming:
            raise ProcessError(
                "Repeated incoming %s with id='%s' "
                "while waiting for and completion"
                %(transition, transition.id))
        self.incoming += (transition.id, )
        self.process.refreshXorGateways()

        if len(self.incoming) < len(definition.incoming):
            return  # not enough incoming yet

        registry = get_current_registry()
        registry.notify(ActivityStarted(self))

        # Execute all possible transitions
        self._finish()

    def _createWorkItems(self, gw, node_ids):
        process = gw.process
        gwdef = gw.definition
        # If the node is a and-join gateway and we have and instance of it,
        # and all incoming transitions minus the one we use are there,
        # we continue
        # FIXME very that we have all incoming workitems
#        instances = [n for n in process.nodes.values() if n.definition is self]
        instances = []
        if not instances:
            raise StopIteration
        gw = instances[0]
        if len(gw.incoming) + 1 != len(gwdef.incoming):
            raise StopIteration

        for transition in self.definition.outgoing:
            if transition.sync or transition.condition(process):
                node = process.nodes[transition.to]
                for wi_tuple in node._createWorkItems(gw,
                        node_ids + (transition.to,)):
                    yield wi_tuple


# parallel avec condition avec default
class InclusiveGateway(Gateway):
    pass
