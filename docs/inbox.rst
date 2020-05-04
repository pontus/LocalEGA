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

The S3 Proxy uses access tokens as the main authentication mechanism.

The sda authentication service (https://github.com/NBISweden/sda-auth) is designed to convert
CEGA REST endpoint authentication to a JWT that can be used when uploading to the S3 proxy.

The proxy requires the user to set the bucket name the same as the username when uploading data,
``s3cmd put FILE s3://USER_NAME/path/to/file``

Configuration
^^^^^^^^^^^^^

The S3 proxy server can be configured via a yaml formatted file with the
top level blocks, ``aws:``, ``broker:`` and ``server:``.

ENVs take precedence over file based configurations.


Environment variables used:

+----------------------+--------------------+--------------------------+
| Variable name        | Default value      | Description              |
+======================+====================+==========================+
| AWS_URL              |                    | Inbox S3 backend URL     |
+----------------------+--------------------+--------------------------+
| AWS_ACCESSKEY        |                    | Inbox S3 backend access  |
|                      |                    | key                      |
+----------------------+--------------------+--------------------------+
| AWS_SECRETKEY        |                    | Inbox S3 backend secret  |
|                      |                    | key                      |
+----------------------+--------------------+--------------------------+
| AWS_REGION           | us-east-1          | Inbox S3 backend region  |
+----------------------+--------------------+--------------------------+
| AWS_BUCKET           |                    | S3 backend bucket name   |
+----------------------+--------------------+--------------------------+
| AWS_READYPATH        |                    | Path on the S3 backend   |
|                      |                    | that reports readiness   |
+----------------------+--------------------+--------------------------+
| AWS_CACERT           |                    | CA file to useif the S3  |
|                      |                    | backend is private       |
+----------------------+--------------------+--------------------------+
| BROKER_HOST          |                    | RabbitMQ broker host     |
+----------------------+--------------------+--------------------------+
| BROKER_USER          |                    | RabbitMQ broker          |
|                      |                    | username                 |
+----------------------+--------------------+--------------------------+
| BROKER_PASSWORD      |                    | RabbitMQ broker          |
|                      |                    | password                 |
+----------------------+--------------------+--------------------------+
| BROKER_PORT          |                    | RabbitMQ broker port     |
+----------------------+--------------------+--------------------------+
| BROKER_VHOST         |                    | RabbitMQ broker vhost    |
+----------------------+--------------------+--------------------------+
| BROKER_exchange      |                    | RabbitMQ exchange to     |
|                      |                    | publish to               |
+----------------------+--------------------+--------------------------+
| BROKER_ROUTINGKEY    |                    | Routing key used when    |
|                      |                    | publishing messages      |
+----------------------+--------------------+--------------------------+
| BROKER_SSL           |                    | Use AMQPS for broker     |
|                      |                    | connection               |
+----------------------+--------------------+--------------------------+
| BROKER_CACERT        |                    | CA cert used for broker  |
|                      |                    | connectivity             |
+----------------------+--------------------+--------------------------+
| BROKER_VERIFYPEER    |                    | Enforce mTLS for broker  |
|                      |                    | connection               |
+----------------------+--------------------+--------------------------+
| BROKER_CLIENTCERT    |                    | Client cert used for     |
|                      |                    | beoker connectivity      |
+----------------------+--------------------+--------------------------+
| BROKER_CLINETKEY     |                    | Client key used for      |
|                      |                    | broker connectivity      |
+----------------------+--------------------+--------------------------+
| SERVER_CERT          |                    | Certificate for the S3   |
|                      |                    | endpoint                 |
+----------------------+--------------------+--------------------------+
| SERVER_KEY           |                    | Certificate key for the  |
|                      |                    | S3 endpoint              |
+----------------------+--------------------+--------------------------+
| SERVER_JWTPUBKEYPATH |                    | Path to the folder where |
|                      |                    | the public JWT key is    |
|                      |                    | located                  |
+----------------------+--------------------+--------------------------+
| SERVER_JWTPUBEYURL   |                    | URL to the jwk endpoint  |
|                      |                    | of the OIDC server       |
+----------------------+--------------------+--------------------------+
| SERVER_CONFPATH      | .                  | Path to the folder       |
|                      |                    | where the config file    |
|                      |                    | can be found             |
+----------------------+--------------------+--------------------------+
| SERVER_CONFFILE      | config.yaml        | Full path to the server  |
|                      |                    | config file              |
+----------------------+--------------------+--------------------------+

Sources are located at the separate repo: https://github.com/neicnordic/S3-Upload-Proxy

.. _tsd-file-api:

TSD File API
------------
