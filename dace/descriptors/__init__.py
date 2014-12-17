# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi
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
