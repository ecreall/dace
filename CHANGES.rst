Changelog
=========

1.1.1 (unreleased)
------------------

- Add a remove_unique_process_instances evolve step.

- Add a update_catalogs_evolve evolve step to update catalogs and reindex
  new indexes programmatically.

- On SIGTERM, stop the system thread. It was already done for SIGINT but not
  on SIGTERM.

- Can now execute process_definitions_evolve via sd_evolve script.

- Fix ConflictError at startup when using several workers.

- Fix tests with latest pyramid version.

- Add support for Python 3.6


1.1.0 (2017-02-25)
------------------

- Add user_groups getter to User class, and now include roles from groups
  when checking if the user has given role.


1.0.3 (2017-01-06)
------------------

- Auto evolve TimeEvent if the definition changed.

- Fix the end of a sub-process.

- Optimizations of path finding to get the workitems.


1.0.2 (2016-09-15)
------------------

- Fix an issue with automatic actions.


1.0.1 (2016-08-18)
------------------

- Include mo files in the release.


1.0 (2016-06-28)
----------------

-  Initial version
