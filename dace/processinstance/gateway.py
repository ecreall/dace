from pyramid.threadlocal import get_current_registry

from .core import ActivityFinished, ActivityStarted, ProcessError, FlowNode
from .event import Event
from .workitem import DecisionWorkItem, StartWorkItem
from dace.processdefinition.core import Path


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

    def find_executable_paths(self, source_path, source):
        for transition in self.definition.outgoing:
            if transition.sync or transition.condition(self.process):
                nodedef = self.process[transition.target.__name__]
                initial_path = source_path.clone()
                source_transaction = source_path.transaction.__parent__
                source_transaction.remove_subtransaction(source_path.transaction)
                source_transaction.start_subtransaction(type='Find', path=initial_path)
                initial_path.add_transition(transition)
                executable_paths = nodedef.find_executable_paths(initial_path, self)
                for executable_path in executable_paths:
                    yield executable_path

    def start(self, transaction):
        global_transaction = transaction.get_global_transaction()
        registry = get_current_registry()
        notify = registry.notify
        notify(ActivityStarted(self))
        workitems = {}
        allowed_transitions = []
        for transition in self.definition.outgoing:
            if transition.sync or transition.condition(self.process):
                allowed_transitions.append(transition)
                node = self.process[transition.target.__name__]
                initial_path = Path([transition])
                subtransaction = global_transaction.start_subtransaction(type='Find', path=initial_path)
                executable_paths = node.find_executable_paths(initial_path, self)
                for executable_path in executable_paths:
                    dwi = DecisionWorkItem(executable_path, self.process[executable_path.targets[0].__name__])
                    if dwi.node.__name__ in workitems:
                        workitems[dwi.node.__name__].merge(dwi)
                    else:
                        workitems[dwi.node.__name__] = dwi

        if not workitems:
            raise ProcessError("Gateway blocked because there is no workitems")

        i = 0
        for workitem in workitems.values():
            i += 1
            workitem.__name__ = i
            self.addtoproperty('workitems', workitem)

        for decision_workitem in workitems.values():
            node_to_execute = self.process[decision_workitem.path.targets[0].__name__]
            if isinstance(node_to_execute, Event):
                node_to_execute.prepare_for_execution()

    def replay_path(self, decision, transaction):
        allconcernedkitems = self.get_allconcernedworkitems()
        if isinstance(decision, StartWorkItem):
            for wi in allconcernedkitems:
                if decision.path.is_segement(wi.path):
                    decision = wi
                    break

        if decision in allconcernedkitems:
            self.finish_decisions(decision)
        else:
            self.finish_decisions(None)

    def finish_decisions(self, work_item):
        registry = get_current_registry()
        registry.notify(ActivityFinished(self))
        if work_item is not None :
            work_item.validations.append(self.definition)
            if work_item.is_finished:
                work_item.__parent__.delproperty('workitems', work_item)

        # clear commun work items
        allconcernedkitems = self.get_allconcernedworkitems()
        all_stoped_wis = []
        for cdecision in allconcernedkitems:
            if not cdecision in all_stoped_wis and cdecision is not work_item:
               all_stoped_wis.append(cdecision)
               cdecision.validations.append(self.definition)
               cdecision.node.stop()
               if cdecision.is_finished or not cdecision.path.is_segement(work_item.path):
                   cdecision.__parent__.delproperty('workitems', cdecision)

        if work_item is not None:
            transition = work_item.path._get_transitions_source(self.definition)[0]
            self.process.play_transitions(self, [transition])

        paths = self.process.global_transaction.find_allsubpaths_for(self.definition, 'Start')
        if paths:
            for p in set(paths):
                source_transaction = p.transaction.__parent__
                source_transaction.remove_subtransaction(p.transaction)

    def get_allconcernedworkitems(self):
        result = []
        allprocessworkitems = self.process.getWorkItems()
        for wi in allprocessworkitems.values():
            if isinstance(wi, DecisionWorkItem) and self.definition in wi.concerned_nodes():
                result.append(wi)

        return result


# parallel sans condition sans default
class ParallelGateway(Gateway):

    def find_executable_paths(self, source_path, source):
        global_transaction = source_path.transaction.get_global_transaction()
        incoming_nodes = [t.source for t in self.definition.incoming]
        paths = global_transaction.find_allsubpaths_for(self.definition, 'Find')
        test_path = Path()
        for p in paths:
            test_path.add_transition(p.transitions)

        multiple_target = test_path.get_multiple_target()
        if multiple_target:
            for m in multiple_target:
                if isinstance(self.process[m.__name__], ExclusiveGateway):
                    return

        alllatest_transitions = []
        for p in paths:
            alllatest_transitions.extend(p.latest)

        validated_nodes = set([t.source for t in alllatest_transitions])
        startpaths = global_transaction.find_allsubpaths_for(self.definition, 'Start')
        for p in startpaths:
            source_nodes = set([t.source for t in p._get_transitions_target(self.definition)])
            validated_nodes = validated_nodes.union(source_nodes)

        validated = True
        for n in incoming_nodes:
            if not (n in  validated_nodes):
                validated = False
                break

        if validated:
            for transition in self.definition.outgoing:
                if transition.sync or transition.condition(self.process):
                    nodedef = self.process[transition.target.__name__]
                    for p in list(paths):
                        initial_path = p.clone()
                        source_transaction = p.transaction.__parent__
                        source_transaction.remove_subtransaction(p.transaction)
                        source_transaction.start_subtransaction(type='Find', path=initial_path)
                        initial_path.add_transition(transition)
                        executable_paths = nodedef.find_executable_paths(initial_path, self)
                        for executable_path in executable_paths:
                            yield executable_path

    def start(self, transaction):
        global_transaction = transaction.get_global_transaction()
        incoming_nodes = [t.source for t in self.definition.incoming]
        paths = global_transaction.find_allsubpaths_for(self.definition, 'Start')
        validated_nodes = set()
        for p in paths:
            source_nodes = set([t.source for t in p._get_transitions_target(self.definition)])
            validated_nodes = validated_nodes.union(source_nodes)

        if (len(validated_nodes) == len(incoming_nodes)):
            registry = get_current_registry()
            registry.notify(ActivityStarted(self))
            self.play(self.definition.outgoing)
            if paths:
                for p in set(paths):
                    source_transaction = p.transaction.__parent__
                    source_transaction.remove_subtransaction(p.transaction)


# parallel avec condition avec default
class InclusiveGateway(Gateway):
    pass
