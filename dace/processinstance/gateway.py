# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi

from pyramid.threadlocal import get_current_registry

from .core import ActivityFinished, ActivityStarted, FlowNode, MakerFlowNode
from dace.processdefinition.core import Path, Transaction


class Gateway(FlowNode):
    pass# pragma: no cover


# non parallel avec condition avec default
class ExclusiveGateway(Gateway, MakerFlowNode):

    def __init__(self, definition, **kwargs):
        super(ExclusiveGateway, self).__init__(definition, **kwargs)

    def start(self, transaction):
        registry = get_current_registry()
        registry.notify(ActivityStarted(self))
        self.decide(transaction)

    def find_executable_paths(self, source_path, source):
        for transition in self.outgoing:
            if transition.sync or transition.validate(self.process):
                node = transition.target
                initial_path = source_path.clone()
                source_transaction = source_path.transaction.__parent__
                source_transaction.remove_subtransaction(source_path.transaction)
                source_transaction.start_subtransaction(type='Find', 
                                    path=initial_path, initiator=self)
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
                work_item.__parent__.delfromproperty('workitems', work_item)

        # clear commun work items
        allconcernedkitems = self.get_allconcernedworkitems()
        all_stoped_wis = []
        for cdecision in allconcernedkitems:
            if not cdecision in all_stoped_wis and cdecision is not work_item:
                all_stoped_wis.append(cdecision)
                cdecision.validations.append(self)
                if cdecision.is_finished or \
                   not cdecision.path.is_segment(work_item.path):
                    cdecision.node.stop()
                    cdecision.__parent__.delfromproperty('workitems', cdecision)

        if work_item is not None:
            transition = work_item.path._get_transitions_source(self)[0]
            self.process.play_transitions(self, [transition])

        paths = self.process.global_transaction.find_allsubpaths_for(self, 'Start')
        paths.extend(self.process.global_transaction.find_allsubpaths_by_source(self, 'Find'))
        if paths:
            for path in set(paths):
                source_transaction = path.transaction.__parent__
                source_transaction.remove_subtransaction(path.transaction)


# parallel sans condition sans default
class ParallelGateway(Gateway):

    def find_executable_paths(self, source_path, source):
        global_transaction = source_path.transaction.get_global_transaction()
        incoming_nodes = [t.source for t in self.incoming]
        paths = global_transaction.find_allsubpaths_for(self, 'Find')
        test_path = Path()
        for path in paths:
            test_path.add_transition(path.transitions)

        multiple_target = test_path.get_multiple_target
        if multiple_target:
            for node in multiple_target:
                if isinstance(node, ExclusiveGateway):
                    return

        alllatest_transitions = []
        for path in paths:
            alllatest_transitions.extend(path.latest)

        validated_nodes = set([t.source for t in alllatest_transitions])
        # pour le mode replay Start
        startpaths = global_transaction.find_allsubpaths_for(self, 'Start')
        for path in startpaths:
            source_nodes = set([t.source for t in path._get_transitions_target(self)])
            validated_nodes = validated_nodes.union(source_nodes)
        # pour le mode replay End
        validated = True
        for node in incoming_nodes:
            if not (node in  validated_nodes):
                validated = False
                break

        if validated:
            for transition in self.outgoing:
                if transition.sync or transition.validate(self.process):
                    node = transition.target
                    for path in list(paths):
                        initial_path = path.clone()
                        source_transaction = path.transaction.__parent__
                        source_transaction.remove_subtransaction(path.transaction)
                        source_transaction.start_subtransaction(type='Find', 
                                                            path=initial_path, 
                                                            initiator=self)
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
        for path in paths:
            source_nodes = set([t.source for t in path._get_transitions_target(self)])
            validated_nodes = validated_nodes.union(source_nodes)

        if (len(validated_nodes) == len(incoming_nodes)):
            registry = get_current_registry()
            registry.notify(ActivityStarted(self))
            self.play(self.outgoing)
            if paths:
                for path in set(paths):
                    source_transaction = path.transaction.__parent__
                    source_transaction.remove_subtransaction(path.transaction)

    def _refresh_find_transactions(self, transaction):
        global_transaction = transaction.get_global_transaction()
        find_transitions = {}
        startpaths = global_transaction.find_allsubpaths_for(self, 'Find')
        for path in startpaths:
            source_ts = set(path.first)
            for transition in source_ts:
                source_node = transition.source
                if source_node.__name__ in find_transitions:
                    find_transitions[source_node.__name__].append(transition)
                else:
                    find_transitions[source_node.__name__] = [transition]

        re_transaction = Transaction(type='Refresh', initiator=self)
        re_transaction.sub_transactions.extend(list([global_transaction]))
        for key, transitions in find_transitions.items():
            source_node = self.process[key]
            if hasattr(source_node, 'refresh_decisions'):
                source_node.refresh_decisions(
                                re_transaction, transitions)


# parallel avec condition avec default
class InclusiveGateway(Gateway):
    pass# pragma: no cover
