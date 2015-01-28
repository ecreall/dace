# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi

from persistent import Persistent
from zope.interface import Attribute
from pyramid.decorator import reify

from dace.descriptors import SharedUniqueProperty, SharedMultipleProperty
from dace.objectofcollaboration.entity import Entity


class BPMNElementDefinition(Entity):

    def __init__(self, **kwargs):
        super(BPMNElementDefinition, self).__init__(**kwargs)


class FlowNodeDefinition(BPMNElementDefinition):

    incoming = SharedMultipleProperty('incoming', 'target', False)
    outgoing = SharedMultipleProperty('outgoing', 'source', False)
    process = SharedUniqueProperty('process', 'nodes', False)
    factory = Attribute("factory")

    def create(self):
        return self.factory(self)

    def __init__(self, **kwargs):
        super(FlowNodeDefinition, self).__init__(**kwargs)
        self.groups = []
        if 'groups' in kwargs:
            self.groups = kwargs['groups']

    def find_startable_paths(self, source_path, source):
        decision_path = source_path.clone()
        source_transaction = source_path.transaction.__parent__
        source_transaction.remove_subtransaction(source_path.transaction)
        yield decision_path

    def __repr__(self):# pragma: no cover
        return "<%s %r>" % (self.__class__.__name__, self.__name__)


class Transaction(Persistent):

    def __init__(self, path=None ,type='Normal', initiator=None):
        self.path = path
        if self.path is not None and not (self.path.transaction is self):
            self.path.set_transaction(self)

        self.initiator = initiator
        self.sub_transactions = []
        self.__parent__ = None
        self.type = type

    def set_path(self, path):
        self.path = path
        if self.path is not None and not (self.path.transaction is self):
            self.path.set_transaction(self)

    def add_subtransactions(self, subtransactions):
        if not isinstance(subtransactions, (list, tuple)):
            subtransactions = (subtransactions, )

        for sub_t in subtransactions:
            sub_t.__parent__ = self

        self.sub_transactions.extend(subtransactions)

    def remove_subtransaction(self, transaction):
        if self.sub_transactions and transaction in self.sub_transactions:
            self.sub_transactions.remove(transaction)

    def find_allsubpaths_for(self, node, type=None, unique=True):
        path = self.get_path_for(node, type)
        result = []
        if path is not None:
            result.append(path)

        sub_paths = []
        for subtransaction in self.sub_transactions:
            sub_paths.extend(subtransaction.find_allsubpaths_for(node, type))

        if unique:
            sub_paths = [p for p in sub_paths if not p.equal(path)]

        result.extend(sub_paths)

        return result

    def get_path_for(self, node, type=None):
        if self.path is not None and (type is None or type == self.type) and \
           node in self.path.targets:
            return self.path

        return None

    def find_allsubpaths_by_source(self, node, type=None, unique=True):
        path = self.get_path_by_source(node, type)
        result = []
        if path is not None:
            result.append(path)

        sub_paths = []
        for subtransaction in self.sub_transactions:
            sub_paths.extend(subtransaction.find_allsubpaths_by_source(
                                                            node, type))

        if unique:
            sub_paths = [p for p in sub_paths if not p.equal(path)]

        result.extend(sub_paths)
        return result

    def get_path_by_source(self, node, type=None):
        if self.path is not None and (type is None or type == self.type) and \
           node in self.path.sources:
            return self.path

        return None

    def find_allsubpaths_cross(self, node, type=None, unique=True):
        path = self.get_path_cross(node, type)
        result = []
        if path is not None:
            result.append(path)

        sub_paths = []
        for subtransaction in self.sub_transactions:
            sub_paths.extend(subtransaction.find_allsubpaths_cross(node, type))

        if unique:
            sub_paths = [p for p in sub_paths if not p.equal(path)]

        result.extend(sub_paths)
        return result

    def get_path_cross(self, node, type=None):
        if self.path and (type is None or type == self.type) and \
           self.path.contains_node(node):
            return self.path

        return None

    def get_global_transaction(self):
        if self.__parent__ is None:
            return self

        return self.__parent__.get_global_transaction()

    def start_subtransaction(self, 
                             type='Normal', 
                             transitions=None, 
                             path=None,
                             initiator=None):
        transaction = Transaction(path=path, type=type, initiator=initiator)
        if path is None:
            if transitions:
                if not isinstance(transitions, (tuple, list)):
                    transitions = [transitions]
                    
                Path(transitions, transaction)

        self.add_subtransactions(transaction)
        return transaction

    def clean(self):
        self.path = None
        self.sub_transactions = []

    def __repr__(self):# pragma: no cover
        return 'Transaction('+self.type+'):\n' +\
               'Path:'+repr(self.path)+ \
               '\n Sub_Transactions:[\n'+\
               '\n'.join([repr(t) for t in self.sub_transactions])+']'

    #def __eq__(self, other):
    #    return self.path == other.path


class Path(Persistent):

    def __init__(self, transitions=None, transaction=None):
        self.transaction = transaction
        if transaction:
            transaction.set_path(self)

        if transitions is None:
            self.transitions = ()
        else:
            self.transitions = tuple(transitions)

    def _dirty(self):
        try:
            del self.source
        except AttributeError:
            pass

        try:
            del self.targets
        except AttributeError:
            pass

        try:
            del self.is_a_cycle
        except AttributeError:
            pass

        try:
            del self.first
        except AttributeError:
            pass

        try:
            del self.latest
        except AttributeError:
            pass

        try:
            del self.get_multiple_target
        except AttributeError:
            pass

    def set_transaction(self, transaction):
        self.transaction = transaction

    def add_transition(self, transition):
        self._dirty()
        if not isinstance(transition, (list, tuple)):
            transition = (transition, )

        self.transitions += transition

    @reify
    def sources(self):
        if self.is_a_cycle:
            return [self.transitions[0].source]

        return [t.source for t in self.first]

    @reify
    def targets(self):
        if self.is_a_cycle:
            return [self.transitions[-1].target]

        return [t.target for t in self.latest]

    @reify
    def is_a_cycle(self):
        return self.transitions and not self.first and not self.latest

    @reify
    def first(self):
        if self.transitions:
            source_transitions = []
            for transition in self.transitions:
                is_source = True
                for inc in transition.source.incoming:
                    if  self.contains_transition(inc):
                        is_source = False
                        break

                if is_source:
                    source_transitions.append(transition)

            return source_transitions

        return []

    @reify
    def latest(self):
        if self.transitions:
            target_transitions = []
            for transition in self.transitions:
                is_target = True
                for inc in transition.target.outgoing:
                    if  self.contains_transition(inc):
                        is_target = False
                        break

                if is_target:
                    target_transitions.append(transition)

            return target_transitions

        return []

    def next(self, transition):
        if not self.contains_transition(transition):
            return None

        return self._get_transitions_source(transition.target)

    def clone(self):
        cloned = Path(self.transitions, self.transaction)
        return cloned

    def is_segment(self, path):
        for transition in path.transitions:
            eqs = self.contains_transition(transition)
            if not eqs:
                return False

        return True

    def contains_transition(self, transition):
        for transition_ in self.transitions:
            if transition_.equal(transition):
                return True

        return False

    def contains_node(self, node):
        for transition in self.transitions:
            if transition.source is node or transition.target is node:
                return True

        return False

    def _get_transitions_source(self, node):
        return list({(t.source, t.target): t for t in self.transitions \
                      if t.source is node}.values())


    def _get_transitions_target(self, node):
        return list({(t.source, t.target): t for t in self.transitions \
                            if t.target is node}.values())

    @reify
    def get_multiple_target(self):
        results = set()
        for transition in self.transitions:
            transitions = self._get_transitions_source(transition.source)
            if len(transitions) > 1:
                results.add(transition.source)

        return results

    def merge(self, other):
        result = list(self.transitions)
        xor_result = []
        for transition in other.transitions:
            if not self.contains_transition(transition):
                xor_result.append(transition)

        result.extend(xor_result)
        result_path = Path(transitions=result)
        return result_path

    def equal(self, other):
        if other is None:
            return False

        for transition in other.transitions:
            if not (transition in self.transitions):
                return False

        return len(self.transitions) == len(other.transitions)

    def __repr__(self):# pragma: no cover
        return 'Path(' + ', '.join([repr(t) for t in self.transitions]) + ')'


class InvalidProcessDefinition(Exception):
    """A process definition isn't valid in some way.
    """
