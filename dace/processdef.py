from pyramid.events import subscriber
import zope.cachedescriptors.property
from zope.interface import implements
from zope.component import createObject
from zope.component import ComponentLookupError
from zope.component.hooks import getSite
from substanced.interfaces import IObjectAdded

from .interfaces import IProcessDefinition, IProcess
from .core import InvalidProcessDefinition
from .transitiondef import TransitionDefinition
from .process import Process
from .eventdef import StartEventDefinition
from .util import find_catalog


class ProcessDefinition(object):

    implements(IProcessDefinition)

    TransitionDefinitionFactory = TransitionDefinition
    # il faut changer subprocessOnly par  isControlled: Pour les processus imbriques
    isControlled = False
    # pour les sous processus
    isSubProcess = False
    isVolatile = False
    isUnique = False
    def __init__(self, id, integration=None):
        self.id = id
        self.integration = integration
        self.activities = {}
        self.transitions = []
        self.applications = {}
        self.participants = {}
        self.parameters = ()
        self.description = None

    def __repr__(self):
        return "ProcessDefinition(%r)" % self.id

    def defineActivities(self, **activities):
        self._dirty()
        for id, activity in activities.items():
            activity.id = id
            if activity.__name__ is None:
                activity.__name__ = self.id + '.' + id
            activity.process = self
            self.activities[id] = activity

    def defineTransitions(self, *transitions):
        self._dirty()
        self.transitions.extend(transitions)

        # Compute activity transitions based on transition data:
        activities = self.activities
        for transition in transitions:
            activities[transition.from_].transitionOutgoing(transition)
            activities[transition.to].incoming += (transition, )

    def defineApplications(self, **applications):
        for id, application in applications.items():
            application.id = id
            self.applications[id] = application

    def defineParticipants(self, **participants):
        for id, participant in participants.items():
            participant.id = id
            self.participants[id] = participant

    def defineParameters(self, *parameters):
        self.parameters += parameters

    def _start(self):
        # Return an initial transition

        activities = self.activities

        # Find the start, making sure that there is one and that there
        # aren't any activities with no transitions:
        start = ()
        for aid, activity in activities.items():
            if not isinstance(activity, StartEventDefinition) and (not activity.incoming or isConnectedToStartEvent(activities, activity)):
                start += ((aid, activity), )
                if not activity.outgoing:
                    raise InvalidProcessDefinition(
                        "Activity %s has no transitions" %aid)

        if len(start) != 1:
            if start:
                raise InvalidProcessDefinition(
                    "Multiple start activities",
                    [id for (id, a) in start]
                    )
            else:
                raise InvalidProcessDefinition(
                    "No start activities")
        return start[0]

    _start = zope.cachedescriptors.property.Lazy(_start)

    def _dirty(self):
        try:
            del self._start
            del self._startTransition
        except AttributeError:
            pass

    def _startTransition(self):
        aid, activity = self._start
        return self.TransitionDefinitionFactory(None, aid)

    _startTransition = zope.cachedescriptors.property.Lazy(_startTransition)

    def __call__(self, **kwargs):
        try:
            return createObject(self.id,
                                definition = self, startTransition = self._startTransition, **kwargs)
        except ComponentLookupError:
            return Process(self, self._startTransition, **kwargs)

    def createStartWorkItem(self, activity_id=None):
        aid, start_activity = self._start
        startevent = None
        if not start_activity.incoming:
            startevent = start_activity
        else:
            startevent = self.activities[start_activity.incoming[0].from_]

        if isinstance(startevent, StartEventDefinition) and \
            startevent.eventKind is not None:
            return None

        workitems = start_activity.createStartWorkItems(start_activity, (aid,))
        workitems = dict([(wi.node_id, wi) for wi in workitems])
        if activity_id is None:
            return workitems

        return workitems.get(activity_id, None)

    @property
    def isInstantiated(self):
        site_id = getSite().__name__
        created = getattr(self, '_isIntanciated_%s' % site_id, self)
        if created is not self:
            return created
        objectprovides_catalog = find_catalog('objectprovidesindexes')

        object_provides_index = objectprovides_catalog['object_provides']
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


@subscriber(IProcess, IObjectAdded)
def invalidate_isInstantiated_cache(obj, event):
    definition = obj.definition
    site_id = getSite().__name__
    key = '_isIntanciated_%s' % site_id
    if hasattr(definition,  key):
        del definition.__dict__[key]


def isConnectedToStartEvent(activities, activity):
    for c in activity.incoming:
         if isinstance(activities[c.from_], StartEventDefinition):
             return True

    return False
