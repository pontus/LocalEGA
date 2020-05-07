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

local_ega tables
----------------

.. image:: /static/localega-schema.svg
   :target: ./_static/localega-schema.svg
   :alt: localega database schema

main
^^^^
This is the core table of the schema, which holds file identifiers, status, metadata, submission paths and checksum information, archive type information and cryptographic information.

+------------------------------------------+--------------------+
| Column Name                              | Data type          |
+==========================================+====================+
| archive_file_checksum                    | varchar            |
+------------------------------------------+--------------------+
| archive_file_checksum_type               | checksum_algorithm |
+------------------------------------------+--------------------+
| archive_file_reference                   | text               |
+------------------------------------------+--------------------+
| archive_file_size                        | int8               |
+------------------------------------------+--------------------+
| archive_file_type                        | storage            |
+------------------------------------------+--------------------+
| created_at                               | timestamptz        |
+------------------------------------------+--------------------+
| created_by                               | name               |
+------------------------------------------+--------------------+
| encryption_method                        | varchar            |
+------------------------------------------+--------------------+
| header                                   | text               |
+------------------------------------------+--------------------+
| id                                       | int4               |
+------------------------------------------+--------------------+
| last_modified                            | timestamptz        |
+------------------------------------------+--------------------+
| last_modified_by                         | name               |
+------------------------------------------+--------------------+
| stable_id                                | text               |
+------------------------------------------+--------------------+
| status                                   | varchar            |
+------------------------------------------+--------------------+
| submission_file_calculated_checksum      | varchar            |
+------------------------------------------+--------------------+
| submission_file_calculated_checksum_type | checksum_algorithm |
+------------------------------------------+--------------------+
| submission_file_extension                | varchar            |
+------------------------------------------+--------------------+
| submission_file_path                     | text               |
+------------------------------------------+--------------------+
| submission_file_size                     | int8               |
+------------------------------------------+--------------------+
| submission_user                          | text               |
+------------------------------------------+--------------------+
| version                                  | int4               |
+------------------------------------------+--------------------+

errors
^^^^^^
This table keeps records of file submission errors, including information about the submitter and if the submission is active and also the hostname and the error type.

+-------------+-------------+
| Column Name | Data type   |
+=============+=============+
| active      | bool        |
+-------------+-------------+
| error_type  | text        |
+-------------+-------------+
| file_id     | int4        |
+-------------+-------------+
| from_user   | bool        |
+-------------+-------------+
| hostname    | text        |
+-------------+-------------+
| id          | int4        |
+-------------+-------------+
| msg         | text        |
+-------------+-------------+
| occurred_at | timestamptz |
+-------------+-------------+

session_key_checksums_sha256
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Checksums are recorded in order to keep track of already used session keys,

+---------------------------+--------------------+
| Column Name               | Data type          |
+===========================+====================+
| file_id                   | int4               |
+---------------------------+--------------------+
| session_key_checksum      | varchar            |
+---------------------------+--------------------+
| session_key_checksum_type | checksum_algorithm |
+---------------------------+--------------------+

status
^^^^^^
This table holds file statuses, which can range from INIT, IN_INGESTION, ARCHIVED, COMPLETED, READY, ERROR and DISABLED.

+-------------+-----------+
| Column Name | Data type |
+=============+===========+
| code        | varchar   |
+-------------+-----------+
| description | text      |
+-------------+-----------+
| id          | int4      |
+-------------+-----------+

archive_encryption
^^^^^^^^^^^^^^^^^^
It holds the cryptographic strategy used by the archive.

+-------------+-----------+
| Column Name | Data type |
+=============+===========+
| description | text      |
+-------------+-----------+
| mode        | varchar   |
+-------------+-----------+

local_ega views
---------------

archive_files
^^^^^^^^^^^^^

It contains all entries from the main table which are marked as ready.

errors
^^^^^^

It contains error entries from active file submissions.

files
^^^^^

It mirrors the main table containing all records of submitted files.


local_ega functions
-------------------

check_session_keys_checksums_sha256
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
It returns if the session key checksums are already found in the database.

* Inputs: checksums

finalize_file
^^^^^^^^^^^^^
It flags files as READY, by setting their stable id and marking older ingestions as deprecated.

* Inputs: inbox_path, elixir_id, archive_file_checksum, archive_file_checksum_type, stable_id
* Target: local_ega.files

insert_error
^^^^^^^^^^^^
It adds an error entry of a file submission.

* Inputs: file_id, hostname, error_type, msg, from_user
* Target: local_ega.errors

insert_file
^^^^^^^^^^^
It adds a new file entry and deprecates old faulty submissions of the same file if present.

* Inputs: submission_file_path, submission_user
* Target: local_ega.main

is_disabled
^^^^^^^^^^^
It returns whether a given entry is disabled or not.

* Input: file id:

main_updated
^^^^^^^^^^^^
It synchronises the timestamp for each row after update on main.

* Input: None
* Target: local_ega.main

mark_ready
^^^^^^^^^^
It removes all errors of a given entry after it is marked as READY.

* Inputs: None
* Target: mark_ready

local_ega_download tables
-------------------------

.. image:: /static/localega-download-schema.svg
   :target: ./_static/localega-download-schema.svg
   :alt: localega download database schema

requests
^^^^^^^^
It keeps track of all requests made to the file archive, including the requested file chunks and client information.

+------------------+-------------+
| Column Name      | Data type   |
+==================+=============+
| client_ip        | text        |
+------------------+-------------+
| created_at       | timestamptz |
+------------------+-------------+
| end_coordinate   | int8        |
+------------------+-------------+
| file_id          | int4        |
+------------------+-------------+
| id               | int4        |
+------------------+-------------+
| start_coordinate | int8        |
+------------------+-------------+
| user_info        | text        |
+------------------+-------------+

success
^^^^^^^
A record of all successfully downloaded files.

+-------------+--------------+
| Column Name | Data type    |
+=============+==============+
| bytes       | int8         |
+-------------+--------------+
| id          | int4         |
+-------------+--------------+
| occurred_at | timestamptz  |
+-------------+--------------+
| req_id      | int4         |
+-------------+--------------+
| speed       | float8       |
+-------------+--------------+

errors
^^^^^^
A record of all errors occurred during file requests, including the hostname and the error code.

+-------------+-------------+
| Column Name | Data type   |
+=============+=============+
| code        | text        |
+-------------+-------------+
| description | text        |
+-------------+-------------+
| hostname    | text        |
+-------------+-------------+
| id          | int4        |
+-------------+-------------+
| occurred_at | timestamptz |
+-------------+-------------+
| req_id      | int4        |
+-------------+-------------+

local_ega_download functions
----------------------------
download_complete
^^^^^^^^^^^^^^^^^
It marks a file download as complete, and calculates the download speed.
Inputs: requested file id, download size, speed
Target: local_ega_download.success

insert_error
^^^^^^^^^^^^

It adds an error entry of a file download.

* Inputs: requested file id, hostname, error code, error description
* Target: local_ega_download.errors

make_request
^^^^^^^^^^^^

It inserts a new request or reuses and old request entry of a given file.

* Inputs: stable id, user information, client ip, start coordinate and end coordinate
* Target: local_ega_download.requests

