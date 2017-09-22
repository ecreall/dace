.. _declaring_nodes:

.. _node_types:

Node types
==========

StartEventDefinition
^^^^^^^^^^^^^^^^^^^^

Special node for the beginning of the process.

Location: **dace.definition.eventdef.StartEventDefinition**

EndEventDefinition
^^^^^^^^^^^^^^^^^^

Special node for the end of the process.

Location: **dace.definition.eventdef.EndEventDefinition**

ActivityDefinition
^^^^^^^^^^^^^^^^^^

When a process enters in an **ActivityDefinition** node, all its behaviors **start** method are called.

Location: **dace.definition.activitydef.ActivityDefinition**

ExclusiveGatewayDefinition
^^^^^^^^^^^^^^^^^^^^^^^^^^

Exclusive or. If one of the transitions that departs from this node is called, the other ones can't be called anymore.

Location: **dace.definition.gatewaydef.ExclusiveGatewayDefinition**

SubProcessDefinition
^^^^^^^^^^^^^^^^^^^^

TODO

@TODO: other node types