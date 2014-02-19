import logging
from pyramid.i18n import TranslationStringFactory

log = logging.getLogger('dace')
_ =  TranslationStringFactory('dace')

from dace.entity import Entity
from dace.object import Object
from dace.process import Process
from dace.runtime import Runtime
from dace.interfaces import IEntity, IObject, IProcess, IUser, IRuntime

def includeme(config): # pragma: no cover
    config.scan()
