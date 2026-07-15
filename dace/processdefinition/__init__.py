"""Declarative BPMN-like metamodel: ``ProcessDefinition`` plus node,
transition and event definitions. Definitions are plain Python built at
import time and synchronised into ``root['process_definition_container']``
at startup or through the evolve steps.

Beware: ``core.Transaction`` here is the engine's *path-execution*
bookkeeping, not a database transaction (see docs/en/architecture.md).
"""
