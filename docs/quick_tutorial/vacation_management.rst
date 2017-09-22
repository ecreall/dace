.. _qtut_vacation_management:

===================
Vacation management
===================

This tutorial aims to explain the main features of DaCe and how to use it with pyramid and Substance D to create a web app. For this purpose, we will use a vacation management app.

The full source code of this example is available on `github <https://github.com/ecreall/hdm>`_.

Create a Root for your application
----------------------------------

First, you have to create a Root for your application::


  from dace.interfaces import IEntity, IApplication
  from dace.model.application import Application
  from substanced.content import content
  from substanced.util import renamer
  from zope.interface import implementer

  class IRoot(IEntity, IApplication):
      pass

  @content(
    'Root',
    icon='glyphicon glyphicon-home',
    after_create='after_create')
  @implementer(IRoot)
  class Root(Application):

      name = renamer()

      def __init__(self, **kwargs):
          super(Root, self).__init__(**kwargs)

**after_create** method of **Application** will create catalogs after the root object is created.

Create a vacation content
-------------------------

Then, we create a new content::

  from dace.interfaces import IEntity
  from dace.model.entity import Entity
  from substanced.content import content
  from zope.interface import Interface, implementer

  class IVacation(IEntity):
      pass

  @content('vacation', icon='glyphicon glyphicon-home')
  @implementer(IVacation)
  class Vacation(Entity):

      def __init__(self, **kwargs):
          super(Vacation, self).__init__(**kwargs)
          self.set_data(kwargs)


To be able to use your content in DaCe processes, it needs to inherits from **dace.model.entity.Entity** and to implement an interface that inherits from **dace.interfaces.IEntity** (see `zope.interface documentation <https://zopeinterface.readthedocs.io/en/latest/README.html>`_ for more details about interfaces).
Notice that you have to use **self.set_data()** (from **dace.model.object.Object**) to set attributes on your content.

See `Substance D documentation <https://docs.pylonsproject.org/projects/substanced/en/latest/content.html>`_ for more details on content creation.

Then, we add a **vacations** attribute on the **Root** class to indicate that the root object may contain multiple vacation objects::

  from dace.descriptors import CompositeMultipleProperty
  ...
  vacations = CompositeMultipleProperty('vacations')


Adding our first process
------------------------

Here's the first process that we want to implement for our vacation objects::

  start -> pending -> accepted OR refused -> end

After a vacation is created, it goes in *pending* state, then a user can accept or refuse the vacation, then it is the end of the process.

It looks like this in the code::

  @process_definition(
      id='vacation_management',
      title='Request vacation')
  class VacationManagement(ProcessDefinition):

      is_unique = False
      is_volatile = True

      def init_definition(self):
          self.define_nodes(
              start=StartEventDefinition(),
              request_vacation=ActivityDefinition(
                  behaviors=[RequestVacation],
                  description='Employee requests vacation',
                  title='Request vacation'
              ),
              eg=ExclusiveGatewayDefinition(),
              accept=ActivityDefinition(
                  behaviors=[Accept],
                  description='Accept vacation',
                  title='Accept'
              ),
              refuse=ActivityDefinition(
                  behaviors=[Refuse],
                  description='Refuse vacation',
                  title='Refuse'
              ),
              eg1=ExclusiveGatewayDefinition(),
              end=EndEventDefinition()
          )

          self.define_transitions(
              TransitionDefinition('start', 'request'),
              TransitionDefinition('request', 'eg'),
              TransitionDefinition('eg', 'refuse'),
              TransitionDefinition('eg', 'accept'),
              TransitionDefinition('refuse', 'eg1'),
              TransitionDefinition('accept', 'eg1'),
              TransitionDefinition('eg1', 'end'),
          )

We define the node and transitions of the process. For more information about the different types of nodes provided by DaCe, see :ref:`node_types` section.

Behaviors
---------

Let's take a look at **request** node::

  request_vacation=ActivityDefinition(
      behaviors=[RequestVacation],
      description='Employee requests vacation',
      title='Request vacation'
  )

It is an **ActivityDefinition** node that declares a **RequestVacation** behavior. This behavior's start method is called each time a content enters in a **request** node. Here, we create a vacation content and set its state to `pending`. We add it to the **root** content via the **vacations** property that we created earlier on **root**. We also add a relation between the process instance and the vacation content. Here is the code of the behavior::

  class RequestVacation(ElementaryAction):

      context = IRoot

      def start(self, context, request, appstruct, **kw):
          vacation = Vacation(**appstruct)
          vacation.state.append('pending')
          context.addtoproperty('vacations', vacation)
          self.process.execution_context.add_created_entity(
              'vacation', vacation)
          return {'message': 'vacation request added'}