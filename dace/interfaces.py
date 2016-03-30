# Copyright (c) 2014 by Ecreall under licence AGPL terms 
# avalaible on http://www.gnu.org/licenses/agpl.html 

# licence: AGPL
# author: Amen Souissi

from zope.interface import Interface, Attribute as SourceAttribute
from substanced.interfaces import IPrincipal, IFolder, IRoot



class Attribute(SourceAttribute):

    def __init__(self, __name__, __doc__='', **kwargs):
        super(Attribute, self).__init__(__name__, __doc__='')
        for name in kwargs:
            setattr(self, name, kwargs.get(name))


class IObject(IFolder):

    title = Attribute("title")

    created_at = Attribute("created_at")

    modified_at = Attribute("modified_at")


class IEntity(IObject):

    state = Attribute("state", multiplicity='*')

    def getCreator():
        """Get creator with `tag` relation.
        """

    def setCreator(creator):
        """Set the creator with `tag` relation.
        """

    def addInvolvedProcesses(processes):
        pass

    def getInvolvedProcesses():
        pass


class IProfile(IPrincipal, IEntity):
    pass


class IUser(IProfile):

    email = Attribute("email")


class IMachine(IProfile):
    pass


class IGroup(IEntity):
    pass


class IProcess(IEntity):

    definition = Attribute("Process definition")

    workflowRelevantData = Attribute(
        """Workflow-relevant data

        Object with attributes containing data used in conditions and
        to pass data as parameters between applications
        """
        )

    applicationRelevantData = Attribute(
        """Application-relevant data

        Object with attributes containing data used to pass data as
        shared data for applications

        """
        )


class IRuntime(IEntity):
    """Runtime container.
    """
    #contains(IProcess)


class IProcessDefinitionContainer(IEntity):
    """Process definition container.
    """


class IBPMNElement(Interface):
    process = Attribute("Process")


class IWorkItem(Interface):
    """Work items
    """

    id = Attribute(
        """Item identifier

        This identifier is set by the activity instance

        """)

    def start(*arguments):
        """Start the work
        """


class IStartWorkItem(IWorkItem):
    pass


class IDecisionWorkItem(IWorkItem):
    pass


class IProcessDefinition(Interface):
    """Process definition

    A process definition defines a particular workflow and define the control
    and flow of the work. You can think of them as the workflow blueprint.
    """

    id = Attribute("Process-definition identifier")

    __name__ = Attribute("Name")

    description = Attribute("Description")

    activities = Attribute(
        """Process activities

        This is a mapping from activity id to activity definition
        """
        )

    applications = Attribute(
        """Process applications

        This is a mapping from application id to participant definitions
        """
        )

    def defineActivities(**activities):
        """Add activity definitions to the collection of defined activities

        Activity definitions are supplied as keyword arguments.  The
        keywords provide activity identifiers.  The values are
        IActivityDefinition objects.

        """

    def defineTransitions(*transitions):
        """Add transition definitions

        The transitions are ITransition objects.
        """

    def defineApplications(**applications):
        """Declare applications

        The applications are provided as keyword arguments.
        Application identifiers are supplied as the keywords and the
        definitions are supplied as values.  The definitions are
        IApplicationDefinition objects.
        """

    def defineParameters(*parameters):
        """Declate process parameters

        Input parameters are set as workflow-relevant data.  Output
        parameters are passed from workflow-relevant data to the
        processFinished method of process-instances process contexts.

        """


class IActivityDefinition(Interface):
    """Activity definition
    """

    id = Attribute("Activity identifier")

    __name__ = Attribute("Activity Name")

    description = Attribute("Description")

    def addApplication(id, *parameters):
        """Declare that the activity uses the identified activity

        The application identifier must match an application declared
        for the process.

        Parameter definitions can be given as positional arguments.
        The parameter definition directions must match those given in
        the application definition.
        """


class ITransitionDefinition(Interface):
    """Transition definition
    """
    id = Attribute("Transition identifier")

    __name__ = Attribute(
        "Transition name, Text used to identify the Transition.")

    description = Attribute("Description")

    from_ = Attribute(
        "Determines the FROM source of a Transition. (Activity Identifier)")

    to = Attribute(
        "Determines the TO target of a Transition (Activity Identifier)")

    condition = Attribute(
        "A Transition condition expression based on relevant data field.")

class IActivity(Interface):
    """Activity instance
    """

    id = Attribute(
        """Activity identifier

        This identifier is set by the process instance

        """)

    definition = Attribute("Activity definition")

    def workItemFinished(work_item, *results):
        """Notify the activity that the work item has been completed.
        """


class IApplicationDefinition(Interface):
    """Application definition
    """

    __name__ = Attribute("Name")

    description = Attribute("Description")

    parameters = Attribute(
        "A sequence of parameter definitions")


class IParameterDefinition(Interface):
    """Parameter definition
    """

    name = Attribute("Parameter name")

    input = Attribute("Is this an input parameter?")

    output = Attribute("Is this an output parameter?")


class IProcessStarted(Interface):
    """A process has begun executing
    """

    process = Attribute("The process")


class IProcessFinished(Interface):
    """A process has finished executing
    """

    process = Attribute("The process")


class IBusinessAction(Interface):
    pass


class IApplication(IEntity, IRoot):
    pass


class IBehavior(Interface):

    behaviorid = Attribute("Unique identifier")
    title = Attribute("Title")
    description = Attribute("Description")

    def get_validator(cls, **kw):
        """Get validator"""

    def execute(self, context, request, appstruct, **kw):
        """What the behavior is doing"""

    def before_execution(self, context, request, **kw):
        """Executed before the behavior execution (e.g. lock the context)"""

    def after_execution(self, context, request, **kw):
        """Executed after the behavior execution (e.g. unlock the context)"""
