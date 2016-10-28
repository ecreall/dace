.. DaCE documentation master file, created by
   sphinx-quickstart on Fri Oct 28 10:31:47 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=================================
DaCE data-centric workflow engine
=================================

Dace is a data-centric workflow engine. It enables the definition and execution of complex processes and the definition of objects of collaboration. In DaCE the rights management is based on the definition of roles.

It is licensed under a `AGPLv3+ license <http://fsf.org/>`_.

Here is one of the simplest Dace process you can make:

.. literalinclude:: narr/helloworld.py

.. _getting_started:

Getting Started
===============

If you are new to DaCE, we have a few resources that can help you get up to speed right away.

.. toctree::
   :hidden:

   quick_tour
   quick_tutorial/index

* :doc:`quick_tour` gives an overview of the major features in DaCE, covering a little about a lot.

* :doc:`quick_tutorial/index` is similar to the Quick Tour, but in a tutorial format, with somewhat deeper treatment of each topic and with working code.

* For help getting DaCE set up, try :ref:`installing_chapter`.

* Need help?  See :ref:`Support and Development <support-and-development>`.


.. _html_tutorials:

Tutorials
=========

Official tutorials explaining how to use Dace to build various processes, and how to connect Dace processes to various applications.

.. toctree::
   :maxdepth: 1

   tutorials/pontus/index

.. _support-and-development:

Support and Development
=======================

To report bugs, use the `issue tracker
<https://github.com/ecreall/dace/issues>`_.

Browse and check out tagged and trunk versions of Dace via the `DaCE GitHub repository <https://github.com/ecreall/dace/>`_. To check out the trunk via ``git``, use either command:

.. code-block:: text

  # If you have SSH keys configured on GitHub:
  git clone git@github.com:ecreall/dace.git
  
  # Otherwise, HTTPS will work, using your GitHub login:
  git clone https://github.com/ecreall/dace.git


.. _html_narrative_documentation:

Narrative Documentation
=======================

Narrative documentation in chapter form explaining how to use Dace.

.. toctree::
   :maxdepth: 2

   narr/introduction
   narr/install


API Documentation
=================

Comprehensive reference material for every public API exposed by
Dace:

.. toctree::
   :maxdepth: 1
   :glob:

   api/index
   api/*


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

