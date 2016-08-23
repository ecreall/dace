.. This README is meant for consumption by humans and pypi. Pypi can render rst files so please do not use Sphinx features.
   If you want to learn more about writing documentation, please check out: http://docs.plone.org/about/documentation_styleguide_addons.html
   This text does not appear on pypi or github. It is a comment.

============
ecreall_dace
============

DaCE is a data-centric workflow engine. It enables the definition and
execution of complex processes and the definition of objects of collaboration.
In DaCE the rights management is based on the definition of roles.

Features
--------

- Process definition with Activity, Exclusive Gateway, Parallel Gateway,
  Event (StartEvent, IntermediateThrowEvent, IntermediateCatchEvent)
  with the following kind: Terminate, Timer, Signal, Conditional
- Process instances indexed in ZODB with substanced catalog which is based on `hypatia <https://github.com/Pylons/hypatia>`__ indexes.
- eventloop with tornado and zmq is used for conditional and timer events


Examples
--------

This package is used in the following projects:

- `nova-ideo <https://github.com/ecreall/nova-ideo>`__
- `l'agenda commun <https://github.com/ecreall/lagendacommun>`__


Documentation
-------------

TODO


Translations
------------

This product has been translated into

- French


Installation
------------

Add `ecreall_dace` in `install_requires` in your `setup.py`.
and edit `production.ini` in your Pyramid application to add::

    pyramid.includes =
        ...
        dace


Contribute
----------

- Issue Tracker: https://github.com/ecreall/dace/issues
- Source Code: https://github.com/ecreall/dace


License
-------

The project is licensed under the AGPLv3+.
