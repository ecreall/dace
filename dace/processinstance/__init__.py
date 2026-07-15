"""Runtime side of the engine: ``Process`` instances, activities,
gateways (exclusive/parallel), events, work-items and business actions
(``BusinessAction`` and its cardinality flavours), plus locking.
``StartWorkItem`` is virtual: computed from startable paths before any
process instance exists, and consumed to instantiate one.
"""
