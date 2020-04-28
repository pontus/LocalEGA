.. _`inbox login system`:

Inbox login system
==================

Central EGA contains a database of users, with IDs and passwords.

We have developed two solutions both of them allowing user authentication via either a password or
an RSA key against CentralEGA database itself:

* :ref:`apache-mina-inbox`.

Each solution uses CentralEGA's user IDs but can also be extended to
use Elixir IDs (of which we strip the ``@elixir-europe.org`` suffix).

The procedure is as follows: the inbox is started without any created
user. When a user wants to log into the inbox (actually, only ``sftp``
uploads are allowed), the code looks up the username in a local
cache, and, if not found, queries the CentralEGA REST endpoint. Upon
return, we store the user credentials in the local cache and create
the user's home directory. The user now gets logged in if the password
or public key authentication succeeds. Upon subsequent login attempts,
only the local cache is queried, until the user's credentials
expire. The cache has a default TTL of one hour, and is wiped clean
upon reboot (as a cache should).


.. _apache-mina-inbox:

Apache Mina Inbox
-----------------

This solution makes use of `Apache Mina SSHD project <https://mina.apache.org/sshd-project/>`_,
the user is locked within their home folder, which is done by using `RootedFileSystem
<https://github.com/apache/mina-sshd/blob/master/sshd-core/src/main/java/org/apache/sshd/common/file/root/RootedFileSystem.java>`_.

The user's home directory is created upon successful login.
Moreover, for each user, we detect when the file upload is completed and compute its
checksum. This information is provided to CentralEGA via a
:doc:`shovel mechanism on the local message broker <connection>`.
We can configure default cache TTL via ``CACHE_TTL`` environment variable.

Configuration
^^^^^^^^^^^^^

Environment variables used:

+------------------+---------------+
| Variable name    | Default value |
+==================+===============+
| BROKER_USERNAME  | guest         |
+------------------+---------------+
| BROKER_PASSWORD  | guest         |
+------------------+---------------+
| BROKER_HOST      | mq            |
+------------------+---------------+
| BROKER_PORT      | 5672          |
+------------------+---------------+
| INBOX_PORT       | 2222          |
+------------------+---------------+
| INBOX_LOCATION   | /ega/inbox/   |
+------------------+---------------+
| CACHE_TTL        | 3600.0        |
+------------------+---------------+
| CEGA_ENDPOINT    |               |
+------------------+---------------+
| CACHE_TTL        |               |
+------------------+---------------+

Implementation
^^^^^^^^^^^^^^

As mentioned above, the implementation is based on Java library Apache Mina SSHD. It provides a scalable and high
performance asynchronous IO API to support the SSH (and SFTP) protocols.

Sources are located at the separate repo: https://github.com/NBISweden/LocalEGA-inbox
Essentially, it's a Spring-based Maven project, integrated to a common LocalEGA MQ bus.
