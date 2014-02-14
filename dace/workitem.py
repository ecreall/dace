from zope.component import getUtility
from zope.component.interfaces import IFactory
from zope.container.interfaces import INameChooser
from zope.interface import implements, implementedBy
from zope.location.interfaces import ILocation
from zope.event import notify
from zope.lifecycleevent import ObjectAddedEvent, ObjectRemovedEvent
from datetime import datetime, timedelta
import pytz

from persistent.list import PersistentList
from persistent import Persistent

import grok

from .interfaces import (
    IWorkItem, IProcessDefinition, IRuntime, IStartWorkItem, IDecisionWorkItem)



class WorkItemFactory(grok.GlobalUtility):
    grok.implements(IFactory)
    grok.baseclass()
    factory = NotImplemented

    @property
    def title(self):
        return grok.title.bind(default=u"").get(self)

    @property
    def description(self):
        return grok.description.bind(default=u"").get(self)

    def getInterfaces(self):
        return implementedBy(self.factory)

    def __call__(self, *args, **kw):
        return self.factory(*args, **kw)


class StartWorkItem(object):
    implements(IStartWorkItem)

    def __init__(self, application, gwdef, node_ids):
        self.application = application
        self.process_identifier = gwdef.process.id
        self.node_ids = node_ids
        self.process = None
        pd = getUtility(
                IProcessDefinition,
                self.process_identifier)
        self.actions = PersistentList()
        for a in pd.activities[self.node_ids[-1]].contexts:
            self.actions.append(a(self))

    @property
    def process_id(self):
        return self.process_identifier

    @property
    def node_id(self):
        return self.node_ids[-1]

    def start(self, *args):
        pd = getUtility(
                IProcessDefinition,
                self.process_identifier)
        proc = pd()
        proc._v_toreplay = self.node_ids
        proc._v_toreplay_app = self.application
        proc._v_toreplay_context = getattr(self, 'context', None)

        runtime = getUtility(IRuntime)
        #chooser = INameChooser(runtime)
        #name = chooser.chooseName(self.process_identifier, proc)
        #runtime[name] = proc
        runtime.addprocesses(proc)
        definition = pd.applications[self.application]
        data = proc.workflowRelevantData
        for parameter in definition.parameters:
            if parameter.input:
                arg, args = args[0], args[1:]
                setattr(data, parameter.__name__, arg)
        if args:
            raise TypeError("Too many arguments. Expected %s. got %s" %
                            (len(definition.parameters), len(arguments)))
        proc.start()
        self.process = proc
        return proc

    def lock(self, request):
        pass

    def unlock(self, request):
        pass

    def is_locked(self, request):
        return False

    def validate(self):
        # incoming transition is already checked
        return True


class BaseWorkItem(LockableElement, Persistent):
    implements(ILocation)

    context = None
    __parent__ = None

    @property
    def __name__(self):
        return self.id

    def __init__(self, node):
        self.node = node
        self.actions = PersistentList()
        for a in node.definition.contexts:
            self.actions.append(a(self))
        for action in self.actions:
            notify(ObjectAddedEvent(action))

    @property
    def process_id(self):
        return self.node.process.id

    @property
    def node_id(self):
        return self.node.id

    @property
    def process(self):
        return self.node.process

    def validate(self):
        raise NotImplementedError

    def remove(self):
        for a in self.actions:
            notify(ObjectRemovedEvent(a))
        notify(ObjectRemovedEvent(self))
        # This is used in "system" thread to not process the action
        # The gateway workitems were removed by a previous action.
        self._v_removed = True
        self.__parent__ = None


class WorkItem(BaseWorkItem):
    """This is subclassed in generated code.
    """
    implements(IWorkItem)

    def _get_parent(self):
        return self.node

    def _set_parent(self, value):
        self.node = None

    __parent__ = property(_get_parent, _set_parent)

    def __init__(self, node):
        super(WorkItem, self).__init__(node)

    def start(self, *args):
        raise NotImplementedError

    def validate(self):
        activity_id = self.node.definition.id
        node_def = self.node.definition
        if node_def.process.isControlled:
            return True

        # we don't have incoming transition it's a subprocess
        transition = [t for t in node_def.incoming
                if activity_id == t.to][0]
        proc = self.node.process
        return not transition.sync or transition.condition(proc)



class DecisionWorkItem(BaseWorkItem):
    implements(IDecisionWorkItem)

    def _get_parent(self):
        return self.gw

    def _set_parent(self, value):
        self.gw = None

    __parent__ = property(_get_parent, _set_parent)

    def __init__(self, application, gw, node_ids, node):
        self.application = application
        self.gw = gw
        self.node_ids = node_ids
        super(DecisionWorkItem, self).__init__(node)

    def start(self, *args):
        results = args
        self.gw.workItemFinished(self, *results)

    def validate(self):
        """If all transitions (including incoming TODO) are async, return True
        Else if a one transition in the chain is sync,
        verify all transitions condition.
        """
        transitions = []
        # TODO transitions.append(self.gw.incoming_transition)
        node_def = self.gw.definition
        proc_def = self.gw.process.definition
        for node_id in self.node_ids:
            transition = [t for t in node_def.outgoing
                if node_id == t.to][0]
            transitions.append(transition)
            node_def = proc_def.activities[transition.to]
        if not [t for t in transitions if t.sync]:
            return True
        else:
            proc = self.gw.process
            for transition in transitions:
                if not transition.condition(proc):
                    return False

        return True

