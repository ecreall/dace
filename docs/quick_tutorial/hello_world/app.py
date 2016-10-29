from dace.processdefinition.processdef import ProcessDefinition
from dace.processdefinition.activitydef import ActivityDefinition
from dace.processdefinition.transitiondef import TransitionDefinition
from dace.processdefinition.eventdef import (
    StartEventDefinition,
    EndEventDefinition)
from dace.objectofcollaboration.services.processdef_container import (
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
        self.defineNodes(
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
        self.defineTransitions(
            TransitionDefinition('start', 'hello'),
            TransitionDefinition('hello', 'end'),
        )
