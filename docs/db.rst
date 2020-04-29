.. _`db`:

Database Setup
---------------

We use a Postgres database (version 9.6) to store intermediate data,
in order to track progress in file ingestion. The ``lega`` database
schema is as follows.

https://github.com/neicnordic/LocalEGA-db

Look at `the SQL definitions
<https://github.com/neicnordic/LocalEGA-db/tree/master/initdb.d>`_ if
you are also interested in the database triggers.
