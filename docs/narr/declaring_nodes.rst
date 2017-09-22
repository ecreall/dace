.. _declaring_nodes:

.. _node_types:

Node types
==========

Event nodes
-----------

StartEventDefinition
^^^^^^^^^^^^^^^^^^^^

Special node for the beginning of the process.

Location: **dace.definition.eventdef.StartEventDefinition**

EndEventDefinition
^^^^^^^^^^^^^^^^^^

Special node for the end of the process.

Location: **dace.definition.eventdef.EndEventDefinition**


EventHandlerDefinition
^^^^^^^^^^^^^^^^^^^^^^

Location: **dace.definition.activitydef.EventHandlerDefinition**

EventDefinition
^^^^^^^^^^^^^^^

Location: **dace.definition.activitydef.EventDefinition**

IntermediateThrowEventDefinition
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Location: **dace.definition.activitydef.IntermediateThrowEventDefinition**

IntermediateCatchEventDefinition
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Location: **dace.definition.activitydef.IntermediateCatchEventDefinition**

EventKindDefinition
^^^^^^^^^^^^^^^^^^^

Location: **dace.definition.activitydef.EventKindDefinition**

SignalEventDefinition
^^^^^^^^^^^^^^^^^^^^^

Location: **dace.definition.activitydef.SignalEventDefinition**

TerminateEventDefinition
^^^^^^^^^^^^^^^^^^^^^^^^

Location: **dace.definition.activitydef.TerminateEventDefinition**

ConditionalEventDefinition
^^^^^^^^^^^^^^^^^^^^^^^^^^

Location: **dace.definition.activitydef.ConditionalEventDefinition**

TimerEventDefinition
^^^^^^^^^^^^^^^^^^^^

Location: **dace.definition.activitydef.TimerEventDefinition**

Activity nodes
--------------

ActivityDefinition
^^^^^^^^^^^^^^^^^^

When a process enters in an **ActivityDefinition** node, all its behaviors **start** method are called.

Location: **dace.definition.activitydef.ActivityDefinition**

SubProcessDefinition
^^^^^^^^^^^^^^^^^^^^

Create a subprocess.

Location: **dace.definition.activitydef.SubProcessDefinition**

Gateway nodes
-------------

ExclusiveGatewayDefinition
^^^^^^^^^^^^^^^^^^^^^^^^^^

Exclusive or. If one of the transitions that departs from this node is called, the other ones can't be called anymore.

Location: **dace.definition.gatewaydef.ExclusiveGatewayDefinition**

ParallelGatewayDefinition
^^^^^^^^^^^^^^^^^^^^^^^^^

Location: **dace.definition.gatewaydef.ParallelGatewayDefinition**

InclusiveGatewayDefinition
^^^^^^^^^^^^^^^^^^^^^^^^^^

Location: **dace.definition.gatewaydef.InclusiveGatewayDefinition**
