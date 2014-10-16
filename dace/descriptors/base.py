from substanced.util import get_oid as get_oid_sd


def get_oid(obj):
    try:
        return get_oid_sd(obj)
    except Exception:
        return None


class Descriptor(object):
    pass
