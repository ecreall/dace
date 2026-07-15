# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Amen Souissi
"""Declarative relation descriptors for collaboration objects.

Four kinds — Composite/Shared x Unique/Multiple. *Composite* implies
containment and lifecycle ownership; *shared* is a reference. Both
maintain the opposite end automatically and are manipulated through
``getproperty``/``setproperty``/``addtoproperty``/``delfromproperty``.
"""
from dace.descriptors.base import Descriptor
from dace.descriptors.compositeunique import CompositeUniqueProperty
from dace.descriptors.compositemultiple import CompositeMultipleProperty
from dace.descriptors.sharedunique import SharedUniqueProperty
from dace.descriptors.sharedmultiple import SharedMultipleProperty

COMPOSITE_UNIQUE = 'cu'
COMPOSITE_MULTIPLE = 'cm'
SHARED_MULTIPLE = 'sm'
SHARED_UNIQUE = 'su'

__properties__ = {COMPOSITE_UNIQUE: CompositeUniqueProperty,
                  SHARED_UNIQUE: SharedUniqueProperty,
                  COMPOSITE_MULTIPLE: CompositeMultipleProperty,
                  SHARED_MULTIPLE: SharedMultipleProperty}
