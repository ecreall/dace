# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi

from substanced.util import get_oid as get_oid_sd


def get_oid(obj):
    try:
        return get_oid_sd(obj)
    except Exception:
        return None


def is_removed(resource):
    if not resource:
        return False
        
    return getattr(resource, '__parent__', None) is None
    

class Descriptor(object):
    pass
