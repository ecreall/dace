# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi

"""Definition-side backbone: nodes, path algebra and its bookkeeping.

``Transaction`` here is the engine's *path-execution* bookkeeping — a
tree of typed explorations (``Start``/``Find``/``Replay``...) — NOT a
database transaction (see docs/en/architecture.md). ``Path`` is an
immutable-ish set of definition transitions with a lazily computed
topology (sources, targets, first/latest transitions, cycles).
"""
from persistent import Persistent
from zope.interface import Attribute
from pyramid.decorator import reify

from dace.descriptors import SharedUniqueProperty, SharedMultipleProperty
from dace.objectofcollaboration.entity import Entity


class BPMNElementDefinition(Entity):

    """Base of every definition element (an ``Entity`` in the definition tree)."""
    def __init__(self, **kwargs):
        super(BPMNElementDefinition, self).__init__(**kwargs)


class FlowNodeDefinition(BPMNElementDefinition):

    """A node of a process definition.

    ``factory`` names the runtime class ``create`` instantiates;
    ``find_startable_paths`` is the definition-side twin of the runtime
    exploration (used before any instance exists, see ``StartWorkItem``).
    """
    incoming = SharedMultipleProperty('incoming', 'target', False)
    outgoing = SharedMultipleProperty('outgoing', 'source', False)
    process = SharedUniqueProperty('process', 'nodes', False)
    factory = Attribute("factory")

    def create(self):
        """Instantiate the runtime node (``factory(self)``)."""
        return self.factory(self)

    def __init__(self, **kwargs):
        super(FlowNodeDefinition, self).__init__(**kwargs)
        self.groups = []
        if 'groups' in kwargs:
            self.groups = kwargs['groups']

    def find_startable_paths(self, source_path, source):
        """Default exploration: a behavioural node ends the path — yield it."""
        decision_path = source_path.clone()
        source_transaction = source_path.transaction.__parent__
        source_transaction.remove_subtransaction(source_path.transaction)
        yield decision_path

    def __repr__(self):# pragma: no cover
        return "<%s %r>" % (self.__class__.__name__, self.__name__)


class Transaction(Persistent):

    """A node of the path-exploration tree (NOT a ZODB transaction).

    Typed (``Normal``/``Start``/``Find``/``Replay``...), optionally carrying
    a ``Path``, with sub-transactions. The ``find_allsubpaths_*`` family
    collects the paths of a given type reaching (``for``), leaving
    (``by_source``) or crossing a node, recursively and deduplicated.
    """
    def __init__(self, path=None ,type='Normal', initiator=None):
        self.path = path
        if self.path is not None and not (self.path.transaction is self):
            self.path.set_transaction(self)

        self.initiator = initiator
        self.sub_transactions = []
        self.__parent__ = None
        self.type = type

    def set_path(self, path):
        """Attach ``path`` (and back-link it to this transaction)."""
        self.path = path
        if self.path is not None and not (self.path.transaction is self):
            self.path.set_transaction(self)

    def add_subtransactions(self, subtransactions):
        """Adopt sub-transaction(s) (sets their ``__parent__``)."""
        if not isinstance(subtransactions, (list, tuple)):
            subtransactions = (subtransactions, )

        for sub_t in subtransactions:
            sub_t.__parent__ = self

        self.sub_transactions.extend(subtransactions)

    def remove_subtransaction(self, transaction):
        """Drop a direct sub-transaction if present."""
        if self.sub_transactions and transaction in self.sub_transactions:
            self.sub_transactions.remove(transaction)

    def find_allsubpaths_for(self, node, type=None, unique=True):
        """All paths (of ``type``) whose targets include ``node``, recursively."""
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
        """This transaction's path if it matches ``type`` and targets ``node``."""
        if self.path is not None and (type is None or type == self.type) and \
           node in self.path.targets:
            return self.path

        return None

    def find_allsubpaths_by_source(self, node, type=None, unique=True):
        """All paths (of ``type``) whose sources include ``node``, recursively."""
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
        """This transaction's path if it matches ``type`` and starts at ``node``."""
        if self.path is not None and (type is None or type == self.type) and \
           node in self.path.sources:
            return self.path

        return None

    def find_allsubpaths_cross(self, node, type=None, unique=True):
        """All paths (of ``type``) that contain ``node`` anywhere, recursively."""
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
        """This transaction's path if it matches ``type`` and crosses ``node``."""
        if self.path and (type is None or type == self.type) and \
           self.path.contains_node(node):
            return self.path

        return None

    def get_global_transaction(self):
        """Climb to the root of the exploration tree."""
        if self.__parent__ is None:
            return self

        return self.__parent__.get_global_transaction()

    def start_subtransaction(self, 
                             type='Normal', 
                             transitions=None, 
                             path=None,
                             initiator=None):
        """Open a typed sub-exploration (building a ``Path`` from ``transitions`` if given)."""
        transaction = Transaction(path=path, type=type, initiator=initiator)
        if path is None:
            if transitions:
                if not isinstance(transitions, (tuple, list)):
                    transitions = [transitions]
                    
                Path(transitions, transaction)

        self.add_subtransactions(transaction)
        return transaction

    def clean(self):
        """Reset path and sub-transactions."""
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

    """An ordered set of definition transitions with lazy topology.

    ``first``/``latest`` are the boundary transitions, ``sources``/
    ``targets`` the boundary nodes (single-looped when ``is_a_cycle``);
    ``get_multiple_target`` spots fork points. The reified attributes are
    invalidated by ``_dirty`` whenever transitions change.
    """
    def __init__(self, transitions=None, transaction=None):
        self.transaction = transaction
        if transaction:
            transaction.set_path(self)

        if transitions is None:
            self.transitions = ()
        else:
            self.transitions = tuple(transitions)

    def _dirty(self):
        """Invalidate the reified topology after a mutation."""
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
        """Bind this path to its owning (path) transaction."""
        self.transaction = transaction

    def add_transition(self, transition):
        """Append transition(s) and invalidate the topology."""
        self._dirty()
        if not isinstance(transition, (list, tuple)):
            transition = (transition, )

        self.transitions += transition

    @reify
    def sources(self):
        """Boundary source nodes (cycle: the first source)."""
        if self.is_a_cycle:
            return [self.transitions[0].source]

        return [t.source for t in self.first]

    @reify
    def targets(self):
        """Boundary target nodes (cycle: the last target)."""
        if self.is_a_cycle:
            return [self.transitions[-1].target]

        return [t.target for t in self.latest]

    @reify
    def is_a_cycle(self):
        """True when the path has transitions but no boundary."""
        return self.transitions and not self.first and not self.latest

    @reify
    def first(self):
        """Transitions whose source has no incoming transition inside the path."""
        source_transitions = []
        for transition in self.transitions:
            is_source = True
            for inc in transition.source.incoming:
                if self.contains_transition(inc):
                    is_source = False
                    break

            if is_source:
                source_transitions.append(transition)

        return source_transitions

    @reify
    def latest(self):
        """Transitions whose target has no outgoing transition inside the path."""
        target_transitions = []
        for transition in self.transitions:
            is_target = True
            for inc in transition.target.outgoing:
                if self.contains_transition(inc):
                    is_target = False
                    break

            if is_target:
                target_transitions.append(transition)

        return target_transitions

    def next(self, transition):
        """The transitions leaving the target of ``transition`` inside the path."""
        return self._get_transitions_source(transition.target)

    def clone(self):
        """Copy (same transitions, same transaction)."""
        cloned = Path(self.transitions, self.transaction)
        return cloned

    def is_segment(self, path):
        """True when every transition of ``path`` is contained in this one."""
        for transition in path.transitions:
            eqs = self.contains_transition(transition)
            if not eqs:
                return False

        return True

    def contains_transition(self, transition):
        """Membership by ``Transition.equal`` (id)."""
        for transition_ in self.transitions:
            if transition_.equal(transition):
                return True

        return False

    def contains_node(self, node):
        """True when ``node`` is an end of any contained transition."""
        for transition in self.transitions:
            if transition.source is node or transition.target is node:
                return True

        return False

    def _get_transitions_source(self, node):
        """Contained transitions leaving ``node``."""
        return {t for t in self.transitions if t.source is node}


    def _get_transitions_target(self, node):
        """Contained transitions reaching ``node``."""
        return {t for t in self.transitions if t.target is node}

    @reify
    def get_multiple_target(self):
        """Nodes from which several contained transitions leave (forks)."""
        results = set()
        for transition in self.transitions:
            transitions = self._get_transitions_source(transition.source)
            if len(transitions) > 1:
                results.add(transition.source)

        return results

    def merge(self, other):
        """New path = these transitions plus the missing ones of ``other``."""
        result = list(self.transitions)
        xor_result = []
        for transition in other.transitions:
            if not self.contains_transition(transition):
                xor_result.append(transition)

        result.extend(xor_result)
        result_path = Path(transitions=result)
        return result_path

    def equal(self, other):
        """Same transitions (by id), same count."""
        if other is None:
            return False

        for transition in other.transitions:
            if not transition in self.transitions:
                return False

        return len(self.transitions) == len(other.transitions)

    def __repr__(self):# pragma: no cover
        return 'Path(' + ', '.join([repr(t) for t in self.transitions]) + ')'


class InvalidProcessDefinition(Exception):
    """A process definition isn't valid in some way.
    """
