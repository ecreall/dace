# -*- coding: utf-8 -*-
# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi

from zope.processlifetime import IDatabaseOpenedWithRoot
from pyramid.events import subscriber
from pyramid.threadlocal import get_current_request

from substanced.event import RootAdded

from .interfaces import IProcessDefinitionAdded
from .processdef_container import create_process_definition_container


@subscriber(RootAdded)
def add_process_definition_container(event):
    root = event.object
    request = get_current_request()
    request.root = root
    create_process_definition_container(root)



@subscriber(IDatabaseOpenedWithRoot)
def remove_definitions(event):
    db = event.database
    root = db.open().root()['app_root']
    def_container = root['process_definition_container']
    for definition in list(def_container.definitions):
        if hasattr(definition, '_broken_object'):
        	name = definition.__name__
        	def_container.remove(name, send_events=False)
        	def_container._definitions_value.remove(name)