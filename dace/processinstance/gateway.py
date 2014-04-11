from pyramid.threadlocal import get_current_registry

from .core import ActivityFinished, ActivityStarted, ProcessError, FlowNode, MakerFlowNode
from .event import Event
from .workitem import DecisionWorkItem, StartWorkItem
from dace.processdefinition.core import Path, Transaction


class Gateway(FlowNode):
    pass

# non parallel avec condition avec default
class ExclusiveGateway(Gateway, MakerFlowNode):

    def __init__(self, definition):
        super(ExclusiveGateway, self).__init__(definition)

    def start(self, transaction):
        registry = get_current_registry()
        registry.notify(ActivityStarted(self))
        self.decide(transaction)

    def find_executable_paths(self, source_path, source):
        for transition in self.outgoing:
            if transition.sync or transition.condition(self.process):
                node = transition.target
                initial_path = source_path.clone()
                source_transaction = source_path.transaction.__parent__
                source_transaction.remove_subtransaction(source_path.transaction)
                source_transaction.start_subtransaction(type='Find', path=initial_path, initiator=self)
                initial_path.add_transition(transition)
                executable_paths = node.find_executable_paths(initial_path, self)
                for executable_path in executable_paths:
                    yield executable_path

    def finish_decisions(self, work_item):
        registry = get_current_registry()
        registry.notify(ActivityFinished(self))
        if work_item is not None :
            work_item.validations.append(self)
            if work_item.is_finished:
                work_item.__parent__.delproperty('workitems', work_item)

        # clear commun work items
        allconcernedkitems = self.get_allconcernedworkitems()
        all_stoped_wis = []
        for cdecision in allconcernedkitems:
            if not cdecision in all_stoped_wis and cdecision is not work_item:
               all_stoped_wis.append(cdecision)
               cdecision.validations.append(self)
               if cdecision.is_finished or not cdecision.path.is_segement(work_item.path):
                   cdecision.node.stop()
                   cdecision.__parent__.delproperty('workitems', cdecision)

        if work_item is not None:
            transition = work_item.path._get_transitions_source(self)[0]
            self.process.play_transitions(self, [transition])

        paths = self.process.global_transaction.find_allsubpaths_for(self, 'Start')
        paths.extend(self.process.global_transaction.find_allsubpaths_by_source(self, 'Find'))
        if paths:
            for p in set(paths):
                source_transaction = p.transaction.__parent__
                source_transaction.remove_subtransaction(p.transaction)



# parallel sans condition sans default
class ParallelGateway(Gateway):

    def find_executable_paths(self, source_path, source):
        global_transaction = source_path.transaction.get_global_transaction()
        incoming_nodes = [t.source for t in self.incoming]
        paths = global_transaction.find_allsubpaths_for(self, 'Find')
        test_path = Path()
        for p in paths:
            test_path.add_transition(p.transitions)

        multiple_target = test_path.get_multiple_target()
        if multiple_target:
            for m in multiple_target:
                if isinstance(m, ExclusiveGateway):
                    return

        alllatest_transitions = []
        for p in paths:
            alllatest_transitions.extend(p.latest)

        validated_nodes = set([t.source for t in alllatest_transitions])
        #startpaths = global_transaction.find_allsubpaths_for(self, 'Start')
        #for p in startpaths:
        #    source_nodes = set([t.source for t in p._get_transitions_target(self)])
        #    validated_nodes = validated_nodes.union(source_nodes)

        validated = True
        for n in incoming_nodes:
            if not (n in  validated_nodes):
                validated = False
                break

        if validated:
            for transition in self.outgoing:
                if transition.sync or transition.condition(self.process):
                    node = transition.target
                    for p in list(paths):
                        initial_path = p.clone()
                        source_transaction = p.transaction.__parent__
                        source_transaction.remove_subtransaction(p.transaction)
                        source_transaction.start_subtransaction(type='Find', path=initial_path, initiator=self)
                        initial_path.add_transition(transition)
                        executable_paths = node.find_executable_paths(initial_path, self)
                        for executable_path in executable_paths:
                            yield executable_path

    def start(self, transaction):
        self._refresh_find_transactions(transaction)
        global_transaction = transaction.get_global_transaction()
        incoming_nodes = [t.source for t in self.incoming]
        paths = global_transaction.find_allsubpaths_for(self, 'Start')
        validated_nodes = set()
        for p in paths:
            source_nodes = set([t.source for t in p._get_transitions_target(self)])
            validated_nodes = validated_nodes.union(source_nodes)

        if (len(validated_nodes) == len(incoming_nodes)):
            registry = get_current_registry()
            registry.notify(ActivityStarted(self))
            self.play(self.outgoing)
            if paths:
                for p in set(paths):
                    source_transaction = p.transaction.__parent__
                    source_transaction.remove_subtransaction(p.transaction)

    def _refresh_find_transactions(self, transaction):
        global_transaction = transaction.get_global_transaction()
        find_transitions = {}
        startpaths = global_transaction.find_allsubpaths_for(self, 'Find')
        for p in startpaths:
            source_ts = set(p.first)
            for t in source_ts:
                source_node = t.source 
                if source_node.__name__ in find_transitions: 
                    find_transitions[source_node.__name__].append(t)
                else:
                    find_transitions[source_node.__name__] = [t]

        re_transaction = Transaction(type='Refresh', initiator=self)
        re_transaction.sub_transactions.extend(list([global_transaction]))
        for key, ts in find_transitions.iteritems():
            source_node = self.process[key]
            if hasattr(source_node, 'refresh_decisions'):
                t.source.refresh_decisions(re_transaction, ts)

# parallel avec condition avec default
class InclusiveGateway(Gateway):
    pass
