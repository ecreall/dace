# Copyright (c) 2015 by Ecreall under licence AGPL terms 
# available on http://www.gnu.org/licenses/agpl.html

# licence: AGPL
# author: Vincent Fretin, Amen Souissi

"""Alternative inclusion *without* the reactor: scan and evolve steps
only — for processes (scripts, workers) that must not start the
IOLoop/zmq machinery.
"""
from dace import include_evolve_steps


def includeme(config):
    """Scan the package and register the evolve steps (no reactor)."""
    config.scan()
    include_evolve_steps(config)
