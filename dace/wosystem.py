# Copyright (c) 2015 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Vincent Fretin, Amen Souissi

from dace import include_evolve_steps


def includeme(config):
    config.scan()
    include_evolve_steps(config)
