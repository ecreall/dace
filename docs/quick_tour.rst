
.. _quick_tour:

==================
Quick Tour of DaCE
==================

Introduction to business processes
==================================
In a company, a product is usually the result of a sequence of actions, according to business rules, performed by professional actors. The sequence of these actions is called a business process. Some of these actions can be automated in order to simplify the interaction of the different actors with data.

Processes in DaCE
---------------
In DaCE, a process is a set of nodes interconnected by oriented transitions (see Fig 1). These nodes can be actions, events or gateways. 

.. figure:: images/hello-process.png
    :align: center
    :height: 100px
    :alt: hello process
    
    Fig 1: Hello process example


DanCE implement a set of concepts introduced in the BPMN standard. For more informtion about actions, events or gateways see `BPMN Specification - Business Process Model and Notation <http://www.bpmn.org/>`_.

DaCE enables the definition and execution of complex processes. It provide an API to manage processes and their nodes.

Installation
============

Add `ecreall_dace` in `install_requires` in your `setup.py`.
and edit `production.ini` in your Pyramid application to add::

    pyramid.includes =
        ...
        dace

Hello World
===========

Conclusion
==========
