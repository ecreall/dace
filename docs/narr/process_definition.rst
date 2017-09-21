.. _process_definition:

Process definition
==================

A process definition is a class that inherits from **dace.definition.processdef.ProcessDefinition**. Use  **dace.model.services.processdef_container.process_definition** decorator to set the identifier and the title of the process.

The process definition needs to implement the **init_definition** method that declares the nodes of the process and the transitions between these nodes. 

You use **self.define_nodes** to declare the nodes of your process. Each process starts with a **dace.definition.eventdef.StartEventDefinition** node and ends with a **dace.definition.eventdef.EndEventDefinition** node. The types of nodes that you can declare are defined in :ref:`declaring_nodes`.

Then, you use **self.define_transitions** to declare the available transitions for your process nodes. A transition is an instance of **dace.definition.transitiondef.TransitionDefinition**. Its constructor takes the name of the start node and the name of the end node of the transition. See :ref:`transitions` for more details about transitions.

Example
-------
::

  @process_definition(
      id='myprocessid',
      title='My process')
  class MyProcess(ProcessDefinition):

      def init_definition(self):
          # define process nodes
          self.define_nodes(
              # start node: the beginning of the process
              start=StartEventDefinition(),
              # hello node
              hello=ActivityDefinition(
                  # MyBehavior is the behavior to execute
                  # when the node is called
                  behaviors=[MyBehavior],
                  description='Hello behavior',
                  title='Hello!'),
              # end node: the ending of the process
              end=EndEventDefinition(),
          )
          # define transitions between process nodes
          self.define_transitions(
              TransitionDefinition('start', 'hello'),
              TransitionDefinition('hello', 'end'),
          )
