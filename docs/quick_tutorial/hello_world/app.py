from dace.definition.processdef import ProcessDefinition
from dace.definition.activitydef import ActivityDefinition
from dace.definition.transitiondef import TransitionDefinition
from dace.definition.eventdef import (
    StartEventDefinition,
    EndEventDefinition)
from dace.model.services.processdef_container import (
	process_definition)

from .behaviors import (
    MyBehavior,
    )


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
