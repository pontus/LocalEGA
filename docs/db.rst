.. _`db`:

Database Setup
---------------

We use a Postgres database (version 11.6+ ) to store intermediate data,
in order to track progress in file ingestion. The ``lega`` database
schema is as follows.

.. note:: Source code repository for DB component is available at: https://github.com/neicnordic/LocalEGA-db

Look at `the SQL definitions
<https://github.com/neicnordic/LocalEGA-db/tree/master/initdb.d>`_ if
you are also interested in the database triggers.
