.. _data out:

Data Retrieval API
==================

.. note:: Source code repository for Data Out API is available at: https://github.com/neicnordic/LocalEGA-DOA

Configuration
-------------

+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| Variable name                          | Default value                                                        | Description                                        |
+========================================+======================================================================+====================================================+
| ``SSL_ENABLED``                        | true                                                                 | Enables/disables TLS for DOA REST endpoints        |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``KEYSTORE_PATH``                      | /etc/ega/ssl/server.cert                                             | Path to server keystore file                       |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``KEYSTORE_PASSWORD``                  |                                                                      | Password for the keystore                          |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``DB_INSTANCE``                        | db                                                                   | Database hostname                                  |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``DB_PORT``                            | 5432                                                                 | Database port                                      |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``POSTGRES_DB``                        | lega                                                                 | Database name                                      |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``ROOT_CERT_PATH``                     | /etc/ega/ssl/CA.cert                                                 | Path to the CA file for database connectivity      |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``CERT_PATH``                          | /etc/ega/ssl/client.cert                                             | Path to the client cert for database connectivity  |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``CERT_KEY``                           | /etc/ega/ssl/client.key                                              | Path to the client key for database connectivity   |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``POSTGRES_USER``                      | lega_out                                                             | Database username                                  |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``POSTGRES_PASSWORD``                  |                                                                      | Database password                                  |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``S3_ENDPOINT``                        | vault                                                                | S3 server hostname                                 |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``S3_PORT``                            | 443                                                                  | S3 server port                                     |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``S3_ACCESS_KEY``                      | minio                                                                | S3 access key                                      |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``S3_SECRET_KEY``                      | miniostorage                                                         | S3 secret key                                      |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``S3_REGION``                          | us-west-1                                                            | S3 region                                          |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``S3_BUCKET``                          | lega                                                                 | S3 bucket to use                                   |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``S3_SECURE``                          | true                                                                 | true if S3 backend should be accessed over HTTPS   |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``S3_ROOT_CERT_PATH``                  | /etc/ssl/certs/ca-certificates.crt                                   | Path to the CA certs file for S3 connectivity      |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``ARCHIVE_PATH``                       | /                                                                    | Path to the filesystem-archive                     |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``PASSPORT_PUBLIC_KEY_PATH``           | /etc/ega/jwt/passport.pem                                            | Path to the public key for passport JWT validation |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``OPENID_CONFIGURATION_URL``           | https://login.elixir-czech.org/oidc/.well-known/openid-configuration | URL of the OpenID configuration endpoint           |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``VISA_PUBLIC_KEY_PATH``               | /etc/ega/jwt/visa.pem                                                | Path to the public key for visas JWT validation    |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``CRYPT4GH_PRIVATE_KEY_PATH``          | /etc/ega/crypt4gh/key.pem                                            | Path to the Crypt4GH private key                   |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``CRYPT4GH_PRIVATE_KEY_PASSWORD_PATH`` | /etc/ega/crypt4gh/key.pass                                           | Path to the Crypt4GH private key passphrase        |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``LOGSTASH_HOST``                      |                                                                      | Hostname of the Logstash instance (if any)         |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+
| ``LOGSTASH_PORT``                      |                                                                      | Port of the Logstash instance (if any)             |
+----------------------------------------+----------------------------------------------------------------------+----------------------------------------------------+

API Endpoints
-------------

API endpoints listed as OpenAPI specification is available:

.. literalinclude::  ./static/doa-api.yml
    :language: yaml

Handling Permissions
--------------------

Data Out API can be run with connection to an AAI or without.
In the case connection to an AAI provider is not possible the ``PASSPORT_PUBLIC_KEY_PATH`` and
``CRYPT4GH_PRIVATE_KEY_PATH`` need to be set.

.. note:: By default we use Elixir AAI as JWT for authentication
          ``OPENID_CONFIGURATION_URL`` is set to: https://login.elixir-czech.org/oidc/.well-known/openid-configuration

If connected to an AAI provider the current implementation is based on 
`GA4GH Passports <https://github.com/ga4gh/data-security/blob/master/AAI/AAIConnectProfile.md>`_

The AAI JWT payload should contain a GA4GH Passport claim in the scope:

.. code-block:: javascript

    {
        "scope": "openid ga4gh_passport_v1",
        ...
    }

The token is then intended to be delivered to the ``/userinfo`` endpoint at AAI, which will respond with a list of
assorted JWTs gathered from providers that need to be parsed in order to find the relevant information.

.. code-block:: javascript

    {
        "ga4gh_passport_v1": [
            "JWT",
            "JWT",
            "JWT",
            ...
        ]
    }

Each third party token (JWT, RFC 7519) consists of three parts separated by dots, in the following manner: ``header.payload.signature``.
This module processes the assorted tokens to extract the information they carry and to validate that data.
The process is carried out as such:

Dataset permissions are read from GA4GH RI claims of the type "ControlledAccessGrants"

.. code-block:: javascript

    {
        "ga4gh_visa_v1": {
            "type": "ControlledAccessGrants",
            "value": "https://www.ebi.ac.uk/ega/EGAD000000000001",
            "source": "https://ega-archive.org/dacs/EGAC00000000001",
            "by": "dac",
            "asserted": 1546300800,
            "expires": 1577836800
        }
    }

