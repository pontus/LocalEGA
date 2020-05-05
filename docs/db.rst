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

Configuration
^^^^^^^^^^^^^

The following environment variables can be used to configure the database:

+-----------------------------+-----------------------------------+---------------------+
|                Variable     | Description                       | Default value       |
+=============================+===================================+=====================+
|                ``PGVOLUME`` | Mountpoint for the writble volume | /var/lib/postgresql |
+-----------------------------+-----------------------------------+---------------------+
|  ``DB_LEGA_IN_PASSWORD``    | `lega_in`'s password              | -                   |
+-----------------------------+-----------------------------------+---------------------+
| ``DB_LEGA_OUT_PASSWORD``    | `lega_out`'s password             | -                   |
+-----------------------------+-----------------------------------+---------------------+
|                      ``TZ`` | Timezone for the Postgres server  | Europe/stockholm    |
+-----------------------------+-----------------------------------+---------------------+

For TLS support use the variables below:

+---------------------+--------------------------------------------------+-----------------------------------------------------------+
|         Variable    | Description                                      | Default value                                             |
+=====================+==================================================+===========================================================+
| ``PG_SERVER_CERT``  | Public Certificate in PEM format                 | `$PGVOLUME/pg.cert`                                       |
+---------------------+--------------------------------------------------+-----------------------------------------------------------+
|  ``PG_SERVER_KEY``  | Private Key in PEM format                        | `$PGVOLUME/pg.key`                                        |
+---------------------+--------------------------------------------------+-----------------------------------------------------------+
|           ``PG_CA`` | Public CA Certificate in PEM format              | `$PGVOLUME/CA.cert`                                       |
+---------------------+--------------------------------------------------+-----------------------------------------------------------+
| ``PG_VERIFY_PEER``  | Enforce client verification                      | 0                                                         |
+---------------------+--------------------------------------------------+-----------------------------------------------------------+
|        ``SSL_SUBJ`` | Subject for the self-signed certificate creation | `/C=SE/ST=Sweden/L=Uppsala/O=NBIS/OU=SysDevs/CN=LocalEGA` |
+---------------------+--------------------------------------------------+-----------------------------------------------------------+

.. note::  If not already injected, the files located at ``PG_SERVER_CERT`` 
           and ``PG_SERVER_KEY`` will be generated, as a self-signed public/private certificate pair, using ``SSL_SUBJ``.
           Client verification is enforced if and only if ``PG_CA`` exists and ``PG_VERIFY_PEER`` is set to ``1``.