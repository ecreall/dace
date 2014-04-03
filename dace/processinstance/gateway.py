from pyramid.threadlocal import get_current_registry
from substanced.event import ObjectAdded

from .core import ActivityFinished, ActivityStarted, ProcessError, FlowNode
from .event import Event
from .workitem import DecisionWorkItem
from dace.processdefinition.core import Path, Transaction


class Gateway(FlowNode):

    def _refreshWorkItems(self):
        # Unindexes workitems
        self.setproperty('workitems', [])
        i = 0
        for workitem in self._createWorkItems(self, ()):
            i += 1
            #workitem.id = str(i)
            workitem.__name__ = str(i)
            self.addtoproperty('workitems', workitem)


# non parallel avec condition avec default
class ExclusiveGateway(Gateway):

    find_transactions = []

    def find_executable_paths(self, source_path, source):
        for transition in self.definition.outgoing:
            if transition.sync or transition.condition(self.process):
                nodedef = self.process[transition.target.__name__]
                initial_path = source_path.clone()
                source_path.transaction.add_paths(initial_path)
                transition_path = [t for t in self.definition.incoming if t.source.id is source.id][0]
                initial_path.add_transition(transition_path)
                executable_paths = nodedef.find_executable_paths(initial_path, self)
                for executable_path in executable_paths:
                    yield executable_path

    def start(self, transaction):
        subtransaction = transaction.start_subtransaction('Find')
        self.find_transactions.append(subtransaction)
        definition = self.definition
        registry = get_current_registry()
        notify = registry.notify
        notify(ActivityStarted(self))
        workitems = []
        allowed_transitions = []
        for transition in self.definition.outgoing:
            if transition.sync or transition.condition(self.process):
                allowed_transitions.append(transition)
                node = self.process[transition.target.__name__]
                initial_path = Path(subtransaction)
                executable_paths = node.find_executable_paths(initial_path, self)
                for executable_path in executable_paths:
                    #multiple_target = executable_path.get_multiple_target()
                    dwi = DecisionWorkItem(executable_path, self.process[executable_path.target.__name__])
                    workitems.append(dwi)
        
        if not workitems:
            raise ProcessError("Gateway blocked because there is no workitems")
        
        i = 0
        for workitem in workitems:
            i += 1
            workitem.__name__ = i
            self.addtoproperty('workitems', workitem)

        for decision_workitem in workitems:
            node_to_execute = decision_workitem.path.target
            if isinstance(node_to_execute, Event):
                node_to_execute.prepare_for_execution()

    def replay_path(self, path, transaction):
        decision = None
        for dwi in self.workitems:
            if path.is_segement(dwi.path):
                decision = dwi
                break

        self.finich_decisions(decision)

    def finich_decisions(self, work_item):
        # beginning exactly the same as Activity
        if work_item is not None:
            self.delproperty('workitems', work_item)
            work_item.replay_transaction.__parent__.remove_subtransaction(work_item.replay_transaction)
            del work_item.replay_transaction

        self._p_changed = True
        # clear other work items
        for wi in self.workitems:
            wi.node.stop()

        self.setproperty('workitems', [])

        # finish this gateway

        registry = get_current_registry()
        registry.notify(ActivityFinished(self))
        transition = work_item.path._get_transitions_source(self.definition)[0]
        transaction = self.process.global_transaction.start_subtransaction('Start', (transition,))
        self.process.play_transitions(self, [transition], transaction)
        for transaction in list(self.find_transactions):
            transaction.__parent__.remove_subtransaction(transaction)
            self.find_transactions.remove(transaction)

        paths = self.process.global_transaction.find_allsubpaths_for(self, 'Start')
        if paths:
            for p in paths:
                del p



# parallel sans condition sans default
class ParallelGateway(Gateway):

    def find_executable_paths(self, source_path, source):
        global_transaction = source_path.transaction.get_global_transaction()
        incoming_nodes = [t.source for t in self.definition.incoming]
        paths = []
        for n in incoming_nodes:
            paths.extend(global_transaction.find_allsubpaths(n, 'Find'))
        
        test_path = Path()
        for p in paths:
            test_path.add_transition(p.transitions)

        multiple_taget = test_path.get_multiple_target()
        if multiple_target:
            for m in multiple_target:
                if isinstance(self.process[m.__name__],ExclusiveGateway):
                    return 
 
        validated_nodes = set([p.target for p in paths])
        startepaths = global_transaction.find_allsubpaths_for(self.definition, 'Start')
        for p in startepaths:
         validated_nodes.union(set([t.source for t in p._get_transitions_target(self)]))

        if (len(validated_nodes) == len(incoming_nodes)):
            for transition in self.definition.outgoing:
                if transition.sync or transition.condition(self.process):
                    nodedef = self.process[transition.target.__name__]
                    for initial_path in paths:
                        initial_path = source_path.clone()
                        source_path.transaction.add_paths(initial_path)
                        transition_path = [t for t in self.definition.incoming if t.source.id is source.id][0]
                        initial_path.add_transition(transition_path)
                        executable_paths = nodedef.find_executable_paths(initial_path, self)
                        for executable_path in executable_paths:
                            yield executable_path

    def start(self, transaction):
        global_transaction = transaction.get_global_transaction()
        incoming_nodes = [t.source for t in self.definition.incoming]
        paths = global_transaction.find_allsubpaths_for(self, 'Start')
        validated_nodes = set()
        for p in paths:
         validated_nodes.union(set([t.source for t in p._get_transitions_target(self)]))

        if (len(validated_nodes) == len(incoming_nodes)):
            registry = get_current_registry()
            registry.notify(ActivityStarted(self))
            self.play()
            if paths:
                for p in paths:
                    del p


# parallel avec condition avec default
class InclusiveGateway(Gateway):
    pass
