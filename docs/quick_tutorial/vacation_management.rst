.. _qtut_vacation_management:

===================
Vacation management
===================

This tutorial aims to explain the main features of DaCe and how to use it with pyramid and Substance D to create a web app. For this purpose, we will use a vacation management app.

Create a vacation content
-------------------------

First, we create a new content::

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


To be able to use your content in DaCe processes, it needs to inherits from **dace.model.entity.Entity** and to implement an interface that inherits from `IEntity` (see `zope.interface documentation <https://zopeinterface.readthedocs.io/en/latest/README.html>`_ for more details about interfaces).
Notice that you have to use **self.set_data()`` (**dace.model.object.Object**) to set attributes on your content.

See `Substance D documentation <https://docs.pylonsproject.org/projects/substanced/en/latest/content.html>`_ for more details on content creation.
