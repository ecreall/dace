from zope.interface import Interface

from pyramid.view import view_config

from dace.processdefinition.processdef import ProcessDefinition
from dace.processdefinition.activitydef import ActivityDefinition
from dace.processdefinition.transitiondef import TransitionDefinition
from dace.processdefinition.eventdef import (
    StartEventDefinition,
    EndEventDefinition)
from dace.objectofcollaboration.services.processdef_container import (
    process_definition)
from dace.processinstance.activity import ElementaryAction
from dace.util import get_all_business_actions

# Step 1: Define a behavior to execute. This behavior is an
# 'ElementaryAction'. It means that the behavior is executed
# only one time in the process instance.
class MyBehavior(ElementaryAction):
    context = Interface

    def start(self, context, request, appstruct, **kw):
        # Your code hear
        return {'message': 'Hello world!'}


# Step 2: Define the process with her nodes and transitions
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


# Step 3: Define a simple view for find, execute and
# display the result of the execution of our behavior
# defined in our process.
@view_config(name='my_process', renderer='json')
def my_process_view(request):
    # 'get_all_business_actions' enable to retrieve all of
    # behaviors in all of process instances with the id
    # equal to 'myprocessid'
    process_actions = get_all_business_actions(
        context=request.root,
        request=request,
        process_id='myprocessid')
    if process_actions:
        # Get the first action
        action_to_execute = process_actions[0]
        # Get action title
        action_title = action_to_execute.node.title
        # Excute the first action
        result = action_to_execute.execute(
            request.root, request, {})
        # Get the execution result of the behavior.
        # See 'start' method of MyBehavior class
        excution = result.get('message', None)
        # Get the process instance id
        process_id = action_to_execute.process.__name__
        return {'action title': action_title,
                'message': excution,
                'process id': process_id}

    return {}
