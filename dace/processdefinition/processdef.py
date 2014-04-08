from pyramid.events import subscriber
import zope.cachedescriptors.property
from zope.interface import implements
from zope.component import createObject
from zope.component import ComponentLookupError
from zope.component.hooks import getSite

from substanced.interfaces import IObjectAdded

from dace.interfaces import IProcessDefinition, IProcess
from .core import InvalidProcessDefinition, Transaction
from .transitiondef import TransitionDefinition
from dace.processinstance.process import Process
from .eventdef import StartEventDefinition, EndEventDefinition
from .gatewaydef import ParallelGatewayDefinition, ExclusiveGatewayDefinition
from dace.util import find_catalog
from dace.objectofcollaboration.object import Object, COMPOSITE_MULTIPLE

class ProcessDefinition(Object):
    implements(IProcessDefinition)

    properties_def = {'nodes': (COMPOSITE_MULTIPLE, 'process', True),
                      'transitions': (COMPOSITE_MULTIPLE, 'process', True),
                      }
    TransitionDefinitionFactory = TransitionDefinition
    # il faut changer subprocessOnly par  isControlled: Pour les processus imbriques
    isControlled = False
    # pour les sous processus
    isSubProcess = False
    isVolatile = False
    isUnique = False

    def __init__(self, id):
        Object.__init__(self)
        self.id = id
        self.description = None

    def __call__(self, **kwargs):
        try:
            return createObject(self.id,
                                definition = self, startTransition = self._startTransition, **kwargs)
        except ComponentLookupError:
            return Process(self, self._startTransition, **kwargs)

    def _dirty(self):
        try:
            del self._startTransition
        except AttributeError:
            pass

    @property
    def nodes(self):
        return self.getproperty('nodes')

    @property
    def transitions(self):
        return self.getproperty('transitions')

    def __repr__(self):
        return "ProcessDefinition(%r)" % self.id

    def defineNodes(self, **nodes):
        self._dirty()
        for name, node in nodes.items():
            node.id = self.id + '.' + name
            node.__name__ = name
            self.addtoproperty('nodes', node)

    def defineTransitions(self, *transitions):
        self._dirty()
        for transition in transitions:
            transition.__name__ = transition.id
            self.addtoproperty('transitions', transition)
            transition._init_ends()

    def _is_start_orphan(self, node):
        return not isinstance(node, StartEventDefinition) and not node.incoming

    def _is_end_orphan(self, node):
        return not isinstance(node, EndEventDefinition) and not node.outgoing


    def _normalize_definition(self):
        new_transitions = ()
        orphan_nodes = [node for node in self.nodes if self._is_start_orphan(node)]
        if orphan_nodes:
            start_events = self._get_start_events()
            empty_start_event = None
            if start_events:
                for se in start_events:
                    if se.eventKind is None:
                        empty_start_event = se
                        break

            if empty_start_event is None:
                empty_start_event = StartEventDefinition()

            p_g = ParallelGatewayDefinition()
            self.defineNodes(emptystart=empty_start_event, startpg=p_g)
            oldtransitions = list(empty_start_event.outgoing)
            for oldtransition in oldtransitions:
                oldtransition.set_source(p_g) 
  
            new_transitions += (TransitionDefinition('emptystart', 'startpg'), )
            for on in orphan_nodes:
                new_transitions+= (TransitionDefinition('startpg', on.__name__), )

        if new_transitions:
            self.defineTransitions(*new_transitions)
            new_transitions = ()

        orphan_nodes = [node for node in self.nodes if self._is_end_orphan(node)]
        if orphan_nodes:
            end_events = self._get_end_events()
            empty_end_event = None
            if end_events:
                for ee in end_events:
                    if ee.eventKind is None:
                        empty_end_event = ee
                        break

            if empty_end_event is None:
                empty_end_event = EndEventDefinition()

            e_g = ExclusiveGatewayDefinition()
            self.defineNodes(emptyend=empty_end_event, endeg=e_g)
            oldtransitions = list(empty_end_event.incoming)
            for oldtransition in oldtransitions:
                oldtransition.set_target(e_g) 

            new_transitions += (TransitionDefinition('endeg', 'emptyend'), )
            for on in orphan_nodes:
                new_transitions += (TransitionDefinition(on.__name__, 'endeg'), )

        if new_transitions:
            self.defineTransitions(*new_transitions)

        self._normalize_startevents()
        self._normalize_endevents()

    def _normalize_startevents(self):
        start_events = self._get_start_events()
        for se in start_events:
            if len(se.outgoing) > 1:
                p_g = ParallelGatewayDefinition()
                self.defineNodes(mergepg=p_g)
                oldtransitions = list(se.outgoing)
                for oldtransition in oldtransitions:
                    oldtransition.set_source(p_g)

                self.defineTransitions(TransitionDefinition(se.__name__, 'mergepg'))
            
    def _normalize_endevents(self):
        end_events = self._get_end_events()
        for ee in end_events:
            if len(ee.incoming) > 1:
                e_g = ExclusiveGatewayDefinition()
                self.defineNodes(mergeeg=e_g)
                oldtransitions = list(ee.incoming)
                for oldtransition in oldtransitions:
                    oldtransition.set_target(e_g)

                self.defineTransitions(TransitionDefinition('mergeeg', ee.__name__))

    def _get_start_events(self):
        result = []
        for node in self.nodes:
            if isinstance(node, StartEventDefinition):
                result.append(node)

        return result

    def _get_end_events(self):
        result = []
        for node in self.nodes:
            if isinstance(node, EndEventDefinition):
                result.append(node)

        return result    

    def _startTransition(self):
        start_events = self. _get_start_events()
        if len(start_events) != 1:
            raise InvalidProcessDefinition(
                    "Multiple start events",
                    [id for (id, a) in start_events]
                    )

        return start_events[0].outgoing[0]

    _startTransition = zope.cachedescriptors.property.Lazy(_startTransition)

    def start_process(self, node_name=None):
        #une transaction globale pour chaque demande
        self.global_transaction = Transaction()
        start_transition = self._startTransition
        startevent = start_transition.source
        # une trandsaction pour un evenement (pour l'instant c'est un evenement)
        sub_transaction = self.global_transaction.start_subtransaction(type='Find')
        start_workitems = startevent.start_process(sub_transaction)
        start_workitems = dict([(wi.node_name, wi) for wi in start_workitems])
        if node_name is None:
            return start_workitems

        return start_workitems.get(node_name, None)

    def __repr__(self):
        return ''.join([t.__repr__() for t in self.transitions])

    @property
    def isInstantiated(self):
        site_id = getSite().__name__
        created = getattr(self, '_isIntanciated_%s' % site_id, self)
        if created is not self:
            return created

        dace_catalog = find_catalog('dace')
        object_provides_index = dace_catalog['object_provides']
        # TODO: process_id should be indexed for IProcess
        query = object_provides_index.any((IProcess.__identifier__,))
        results = query.execute().all()
        created = False
        for p in results:
            if p.id == self.id:
                created = True
                break

        setattr(self, '_isIntanciated_%s' % site_id, created)
        return created

# TODO pyramid don't support subscriber with two args
#@subscriber(IProcess, IObjectAdded)
def invalidate_isInstantiated_cache(obj, event):
    definition = obj.definition
    site_id = getSite().__name__
    key = '_isIntanciated_%s' % site_id
    if hasattr(definition,  key):
        del definition.__dict__[key]

