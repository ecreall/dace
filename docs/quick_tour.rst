
.. _quick_tour:

==================
Quick Tour of DaCE
==================

Introduction to business processes
==================================
In a company, a product is usually the result of a sequence of actions, according to business rules, performed by professional actors. The sequence of these actions is called a business process. Some of these actions can be automated in order to simplify the interaction of the different actors with data.

Processes in DaCE
-----------------
In DaCE, a process is a set of nodes interconnected by oriented transitions (see Fig 1). These nodes can be actions, events or gateways. 

.. figure:: images/hello-process.png
    :align: center
    :height: 100px
    :alt: hello process
    
    Fig 1: Hello process example


DaCE implement a set of concepts introduced in the BPMN standard. For more informtion about actions, events or gateways see `BPMN Specification - Business Process Model and Notation <http://www.bpmn.org/>`_.

DaCE enables the definition and execution of complex processes. It provide an API to manage processes and their nodes.

DaCE is an application built using the `SubstanceD <http://www.substanced.net/>`_ application server and the `Pyramid <http://www.pylonsproject.org/>`_ web framework.

Installation
============

If you have already installed Substance D
-----------------------------------------

#. Add `ecreall_dace` in `requires` in the `setup.py` file.::

    ...
    requires = [
        ...
        'ecreall_dace',
        ]
    ...

#. Include DaCE in the Pyramid configurator in the ``myproj/__init__.py`` file::

    ...
    def main(global_config, **settings):
        ...
        config.include('substanced')
        # include dace in the Pyramid configurator
        config.include('dace')
        ...


If you didn't already installed SubstanceD
------------------------------------------

You can install DaCE by performing the following steps.

#. Create a new directory somewhere and ``cd`` to it::

   $ virtualenv -p python3.4 hack-on-substanced
   $ cd hack-on-substanced
   $ . bin/activate

#. Install Substance D either from PyPI or from a git checkout::

   $ pip install substanced
   
   OR::
   
   $ pip install git+https://github.com/Pylons/substanced#egg=substanced

   Alternatively create a writeable fork on GitHub and check that out.
   
#. Check that the python-magic library has been installed::

   $ python -c "from substanced.file import magic; assert magic is not None, 'python-magic not installed'"
   
   If you then see "python-magic not installed" then you will need to take
   additional steps to install the python-magic library.
   
#. Move back to the parent directory::

   $ cd ..

#. Now you should be able to create new Substance D projects by
   using ``pcreate``. The following ``pcreate`` command uses the scaffold
   ``substanced`` to create a new project named ``myproj``::
      
   $ pcreate -s substanced myproj

#. Add `ecreall_dace` in `requires` in the `setup.py` file.::

    ...
    requires = [
        ...
        'ecreall_dace',
        ]
    ...

#. Include DaCE in the Pyramid configurator in the ``myproj/__init__.py`` file::

    ...
    def main(global_config, **settings):
        ...
        config.include('substanced')
        # include dace in the Pyramid configurator
        config.include('dace')
        ...

#. Install that project using ``pip install -e`` into the virtualenv::

   $ pip install -e .

#. Run the resulting project via ``pserve development.ini``. The development server listens to requests sent to `<http://0.0.0.0:6543>`_ by default. Open this URL in a web browser.


Hello World
===========

Applications have shown that learning starts best from a very small first step. Here’s a tiny process definition in DaCE (see Fig 1):

.. literalinclude:: quick_tour/hello_world/app.py
    :linenos:
    :language: python

This simple example is easy to run. Save this as ``process_definition.py`` in your project (``myproj``) and run it.

Next open http://0.0.0.0:6543/my_process in a browser, and you will see the ``Hello World!`` message.

New to DaCE? If so, some lines in the module merit an explanation:

#. *Step 1 - Line 19*. The ``ElementaryAction`` is one of multiple behavior type in DaCE. This type of behavior is executed only one time in the process instance. See :ref:`Behaviors types <behaviors_types>` for more information.

#. *Step 1 - Line 20*. The behavior is executed only on objects that implement the ``context``.

#. *Step 3 - Line 63*. ``getAllBusinessAction`` retrieves all of behaviors in all of process instances of myprocessid for a given object. For more information about the DaCE utilities see :ref:`DaCE utilities <dace_utilities>`

.. seealso::
   :ref:`Quick Tutorial Hello World <qtut_hello_world>`

