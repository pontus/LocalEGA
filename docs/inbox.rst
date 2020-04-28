.. _`inboxlogin`:

Inbox Login System
==================

Central EGA contains a database of users, with IDs and passwords.

We have developed several solutions allowing user authentication 
against CentralEGA user database:

* :ref:`apache-mina-inbox`;
* :ref:`s3-inbox`;
* :ref:`tsd-file-api`.

Each solution uses CentralEGA's user IDs but can also be extended to
use Elixir IDs (of which we strip the ``@elixir-europe.org`` suffix).

The procedure is as follows: the inbox is started without any created
user. When a user wants to log into the inbox (via ``sftp``, s3 or ``https``),
the inbox service looks up the username in a local queries the CentralEGA REST endpoint. 
Upon return, we store the user credentials in the local cache and create
the user's home directory. The user now gets logged in if the password
or public key authentication succeeds.

.. _apache-mina-inbox:

Apache Mina Inbox
-----------------

This solution makes use of `Apache Mina SSHD project <https://mina.apache.org/sshd-project/>`_,
the user is locked within their home folder, which is done by using ``RootedFileSystem``.

The user's home directory is created upon successful login.
Moreover, for each user, we detect when the file upload is completed and compute its
checksum. This information is provided to CentralEGA via a
:doc:`shovel mechanism on the local message broker <connection>`.
We can configure default cache TTL via ``CACHE_TTL`` environment variable.

Configuration
^^^^^^^^^^^^^

Environment variables used:

+---------------------+--------------------+-------------------------+
| Variable name       | Default value      | Description             |
+=====================+====================+=========================+
| BROKER_USERNAME     | guest              | RabbitMQ broker         |
|                     |                    | username                |
+---------------------+--------------------+-------------------------+
| BROKER_PASSWORD     | guest              | RabbitMQ broker         |
|                     |                    | password                |
+---------------------+--------------------+-------------------------+
| BROKER_HOST         | mq                 | RabbitMQ broker host    |
+---------------------+--------------------+-------------------------+
| BROKER_PORT         | 5672               | RabbitMQ broker port    |
+---------------------+--------------------+-------------------------+
| BROKER_VHOST        | /                  | RabbitMQ broker vhost   |
+---------------------+--------------------+-------------------------+
| INBOX_PORT          | 2222               | Inbox port              |
+---------------------+--------------------+-------------------------+
| INBOX_LOCATION      | /ega/inbox/        | Path to POSIX Inbox     |
|                     |                    | backend                 |
+---------------------+--------------------+-------------------------+
| INBOX_KEYPAIR       |                    | Path to RSA keypair     |
|                     |                    | file                    |
+---------------------+--------------------+-------------------------+
| KEYSTORE_TYPE       | JKS                | Keystore type to use,   |
|                     |                    | JKS or PKCS12           |
+---------------------+--------------------+-------------------------+
| KEYSTORE_PATH       | /etc/ega/inbox.jks | Path to Keystore file   |
+---------------------+--------------------+-------------------------+
| KEYSTORE_PASSWORD   |                    | Password to access the  |
|                     |                    | Keystore                |
+---------------------+--------------------+-------------------------+
| CACHE_TTL           | 3600.0             | CEGA credentials        |
|                     |                    | time-to-live            |
+---------------------+--------------------+-------------------------+
| CEGA_ENDPOINT       |                    | CEGA REST endpoint      |
+---------------------+--------------------+-------------------------+
| CEGA_ENDPOINT_CREDS |                    | CEGA REST credentials   |
+---------------------+--------------------+-------------------------+
| S3_ENDPOINT         | inbox-backend:9000 | Inbox S3 backend URL    |
+---------------------+--------------------+-------------------------+
| S3_REGION           | us-east-1          | Inbox S3 backend region |
|                     |                    | (us-east-1 is default   |
|                     |                    | in Minio)               |
+---------------------+--------------------+-------------------------+
| S3_ACCESS_KEY       |                    | Inbox S3 backend access |
|                     |                    | key (S3 disabled if not |
|                     |                    | specified)              |
+---------------------+--------------------+-------------------------+
| S3_SECRET_KEY       |                    | Inbox S3 backend secret |
|                     |                    | key (S3 disabled if not |
|                     |                    | specified)              |
+---------------------+--------------------+-------------------------+
| USE_SSL             | true               | true if S3 Inbox        |
|                     |                    | backend should be       |
|                     |                    | accessed by HTTPS       |
+---------------------+--------------------+-------------------------+
| LOGSTASH_HOST       |                    | Hostname of the         |
|                     |                    | Logstash instance (if   |
|                     |                    | any)                    |
+---------------------+--------------------+-------------------------+
| LOGSTASH_PORT       |                    | Port of the Logstash    |
|                     |                    | instance (if any)       |
+---------------------+--------------------+-------------------------+


As mentioned above, the implementation is based on Java library Apache Mina SSHD.

Sources are located at the separate repo: https://github.com/neicnordic/LocalEGA-inbox
Essentially, it's a Spring-based Maven project, integrated with the :ref:`mq`.


.. _s3-inbox:

S3 Proxy Inbox
--------------


.. _tsd-file-api:

TSD File API
------------