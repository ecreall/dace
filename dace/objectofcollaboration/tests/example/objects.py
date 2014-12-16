# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi
from zope.interface import implementer

from dace.interfaces import IObject
from dace.objectofcollaboration.object import Object
from dace.descriptors import (
                CompositeUniqueProperty,
                SharedUniqueProperty,
                CompositeMultipleProperty,
                SharedMultipleProperty)
from dace.objectofcollaboration.entity import Entity
from dace.objectofcollaboration.principal.role import Collaborator, Role, Administrator, role


class Object1(Object):
    composition_u = CompositeUniqueProperty('composition_u', 'shared2_u', False)
    composition_m = CompositeMultipleProperty('composition_m', 'shared21_u', False)
    shared_u = SharedUniqueProperty('shared_u', 'shared22_u', False)
    shared_m = SharedMultipleProperty('shared_m', 'shared23_u', False)


class Object2(Object):
    shared2_u = SharedUniqueProperty('shared2_u', 'composition_u', False)
    shared21_u = SharedUniqueProperty('shared21_u', 'composition_m', False)
    shared22_u = SharedUniqueProperty('shared22_u', 'shared_u', False)
    shared23_u = SharedUniqueProperty('shared23_u', 'shared_m', False)


class ObjectShared(Object):
    shared = SharedUniqueProperty('shared', None, False)
    shared_m = SharedMultipleProperty('shared_m', None, False)


class IObjectA(IObject):
    pass


class IObjectB(IObject):
    pass


class IObjectC(IObjectB):
    pass


@implementer(IObjectA)
class ObjectA(Entity):
    composition_mu = CompositeMultipleProperty('composition_mu', None, False)


@implementer(IObjectB)
class ObjectB(Object):
    pass


@implementer(IObjectC)
class ObjectC(ObjectB):
    pass


@role(name='Developer', superiors=[Administrator], lowers=[Collaborator])
class Developer(Role):
    pass