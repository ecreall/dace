# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi
# -*- coding: utf-8 -*-
from pyramid.events import subscriber

from substanced.event import RootAdded

from .interfaces import IProcessDefinitionAdded
from .processdef_container import create_process_definition_container


@subscriber(RootAdded)
def add_process_definition_container(event):
    root = event.object
    create_process_definition_container(root)


@subscriber(IProcessDefinitionAdded)
def add_process_def(event):
    definition = event.object
    definition._init_definition()
