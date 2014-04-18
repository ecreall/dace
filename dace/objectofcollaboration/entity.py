from zope.interface import implements
from persistent.list import PersistentList

from substanced.util import get_oid

from dace.interfaces import IEntity
from .object import Object, SHARED_UNIQUE, SHARED_MULTIPLE
from dace.util import getAllBusinessAction
from dace.relations import find_relations


class ActionCall(object):
    # il faut faire ici un delegation des attribut de l'action en question
    def __init__(self, action, obj):
        super(ActionCall, self).__init__()
        self.object = obj
        self.action = action
        self.title = self.action.title
        self.process = self.action.process

    @property
    def url(self):
        return self.action.url(self.object)

    @property
    def content(self):
        return self.action.content(self.object)


class Entity(Object):
    implements(IEntity)

    properties_def = {'creator': (SHARED_UNIQUE, 'createds', True),
                      'involvers': (SHARED_MULTIPLE, 'involveds', True)}

    def __init__(self, **kwargs):
        Object.__init__(self)
        self.state = PersistentList()
        self.__property__ = None

    def setstate(self, state):
        if not isinstance(state, (list, tuple)):
            state = [state]

        self.state = PersistentList()
        for s in state:
            self.state.append(s)

    @property
    def creator(self):
        ec_creator = self.getproperty('creator')
        if ec_creator is not None: 
            return ec_creator.process

        return None

    @property
    def involvers(self):
        return [e.process for e in self.getproperty('involvers')]

    @property
    def actions(self):
        allactions = getAllBusinessAction(self)
        return [ActionCall(a, self) for a in allactions]

    #les relations avec le processus sont des relations d'agregation multiple bidirectionnelles
    # il faut donc les difinir comme des properties

